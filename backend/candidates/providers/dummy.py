"""Deterministic in-memory communication provider for development and tests.

Send outcomes are decided, in order, by:

1. Scripted outcomes queued via `scripted_outcomes` / `queue_outcomes()`.
2. Validation: recipients without 7-15 digits and blank or oversized bodies
   fail permanently.
3. Magic recipient suffixes (digits only):
   - ending in ``0000``: permanent failure (invalid recipient)
   - ending in ``9999``: temporary failure on every attempt
   - ending in ``9998``: temporary failure on the first attempt to that
     number, success afterwards (useful for demonstrating retries)
4. Otherwise the send succeeds.
"""
import re
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from enum import StrEnum

from .base import BaseProvider, DeliveryStatus, ErrorCode, SendResult, StatusUpdate

MIN_RECIPIENT_DIGITS = 7
MAX_RECIPIENT_DIGITS = 15
MAX_BODY_LENGTH = 1600

PERMANENT_FAILURE_SUFFIX = '0000'
TEMPORARY_FAILURE_SUFFIX = '9999'
FLAKY_SUFFIX = '9998'


class Outcome(StrEnum):
    SUCCESS = 'success'
    TEMPORARY_FAILURE = 'temporary_failure'
    PERMANENT_FAILURE = 'permanent_failure'


class DummyProvider(BaseProvider):
    name = 'dummy'

    def __init__(self, scripted_outcomes=None):
        self._lock = threading.Lock()
        self._scripted = deque(Outcome(o) for o in (scripted_outcomes or ()))
        self._flaky_attempted = set()

    def queue_outcomes(self, *outcomes):
        with self._lock:
            self._scripted.extend(Outcome(o) for o in outcomes)

    def send(self, recipient, body):
        try:
            return self._send(recipient, body)
        except Exception as exc:  # Providers report failures as results, never exceptions.
            return SendResult.failure(ErrorCode.PROVIDER_ERROR, f'Unexpected provider error: {exc}')

    def _send(self, recipient, body):
        scripted = self._next_scripted()
        if scripted is not None:
            return self._result_for(scripted)

        digits = re.sub(r'\D', '', recipient or '')
        if not MIN_RECIPIENT_DIGITS <= len(digits) <= MAX_RECIPIENT_DIGITS:
            return SendResult.failure(
                ErrorCode.INVALID_RECIPIENT, 'Recipient phone number is not valid.'
            )
        if not body or not body.strip():
            return SendResult.failure(ErrorCode.BODY_REJECTED, 'Message body is empty.')
        if len(body) > MAX_BODY_LENGTH:
            return SendResult.failure(
                ErrorCode.BODY_REJECTED,
                f'Message body exceeds {MAX_BODY_LENGTH} characters.',
            )

        if digits.endswith(PERMANENT_FAILURE_SUFFIX):
            return self._result_for(Outcome.PERMANENT_FAILURE)
        if digits.endswith(TEMPORARY_FAILURE_SUFFIX):
            return self._result_for(Outcome.TEMPORARY_FAILURE)
        if digits.endswith(FLAKY_SUFFIX):
            with self._lock:
                first_attempt = digits not in self._flaky_attempted
                self._flaky_attempted.add(digits)
            if first_attempt:
                return self._result_for(Outcome.TEMPORARY_FAILURE)

        return self._result_for(Outcome.SUCCESS)

    def _next_scripted(self):
        with self._lock:
            return self._scripted.popleft() if self._scripted else None

    @staticmethod
    def _result_for(outcome):
        if outcome is Outcome.SUCCESS:
            return SendResult.ok(f'dummy_{uuid.uuid4().hex}')
        if outcome is Outcome.TEMPORARY_FAILURE:
            return SendResult.failure(
                ErrorCode.PROVIDER_UNAVAILABLE,
                'Provider temporarily unavailable (simulated). Please retry later.',
            )
        return SendResult.failure(
            ErrorCode.INVALID_RECIPIENT,
            'Recipient is not reachable on this channel (simulated).',
        )

    # Status simulation

    def simulate_status_update(
        self, provider_message_id, status, *, occurred_at=None, event_id=None,
        error_code='', failure_reason='',
    ):
        if status not in DeliveryStatus.ALL:
            raise ValueError(f'Unsupported status {status!r}; expected one of {DeliveryStatus.ALL}.')
        if status == DeliveryStatus.FAILED:
            error_code = error_code or ErrorCode.DELIVERY_FAILED
            failure_reason = failure_reason or 'Message could not be delivered (simulated).'
        return StatusUpdate(
            event_id=event_id or f'evt_{uuid.uuid4().hex}',
            provider_message_id=provider_message_id,
            status=status,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            error_code=error_code,
            failure_reason=failure_reason,
        )

    def simulate_delivered(self, provider_message_id, **kwargs):
        return self.simulate_status_update(provider_message_id, DeliveryStatus.DELIVERED, **kwargs)

    def simulate_read(self, provider_message_id, **kwargs):
        return self.simulate_status_update(provider_message_id, DeliveryStatus.READ, **kwargs)

    def simulate_failed(self, provider_message_id, **kwargs):
        return self.simulate_status_update(provider_message_id, DeliveryStatus.FAILED, **kwargs)
