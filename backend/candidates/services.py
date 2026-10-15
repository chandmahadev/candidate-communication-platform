"""Messaging business logic: sending, bulk sending, retries and provider status updates.

Each message is committed in its own transaction, so one recipient's failure
cannot roll back another recipient's message. Regular sends call the provider
outside any transaction; retries call it while holding a row lock on the
original message so the same failure cannot be retried twice concurrently.
"""
import logging
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Message, MessageStatus, MessageStatusEvent
from .providers import get_provider
from .providers.base import ErrorCode, SendResult, is_retryable

logger = logging.getLogger(__name__)

# Delivery progress order. A message may only move forward along this order;
# FAILED is terminal and can only follow SENT.
STATUS_RANK = {
    MessageStatus.SENT: 0,
    MessageStatus.DELIVERED: 1,
    MessageStatus.READ: 2,
}


class MessagingError(Exception):
    """Base for business-rule errors that the API reports with a code."""

    code = 'messaging_error'

    def __init__(self, detail, **extra):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class RetryNotAllowed(MessagingError):
    code = 'retry_not_allowed'

    def __init__(self, code, detail, **extra):
        super().__init__(detail, **extra)
        self.code = code


class MessageNotFound(MessagingError):
    code = 'message_not_found'


class InvalidStatusTransition(MessagingError):
    code = 'invalid_status_transition'


class EventConflict(MessagingError):
    code = 'event_id_conflict'


# Sending ---------------------------------------------------------------------


def _call_provider(provider, recipient, body):
    try:
        result = provider.send(recipient, body)
    except Exception as exc:
        logger.exception('Provider %s raised during send', getattr(provider, 'name', provider))
        return SendResult.failure(ErrorCode.PROVIDER_ERROR, f'Provider error: {exc}')
    if not isinstance(result, SendResult):
        return SendResult.failure(ErrorCode.PROVIDER_ERROR, 'Provider returned an invalid response.')
    return result


def _record_message(candidate, body, result, retry_of=None):
    fields = {
        'candidate': candidate,
        'body': body,
        'retry_of': retry_of,
        'attempt': retry_of.attempt + 1 if retry_of else 1,
    }
    if result.success:
        fields.update(
            status=MessageStatus.SENT,
            provider_message_id=result.provider_message_id,
            sent_at=timezone.now(),
        )
    else:
        fields.update(
            status=MessageStatus.FAILED,
            error_code=result.error_code or ErrorCode.PROVIDER_ERROR,
            failure_reason=result.error_message or 'Message could not be sent.',
            is_retryable=result.retryable,
        )
    with transaction.atomic():
        return Message.objects.create(**fields)


def send_message(candidate, body, *, retry_of=None, provider=None):
    """Send one message and persist it. Provider failures yield a FAILED message, not an exception."""
    provider = provider or get_provider()
    result = _call_provider(provider, candidate.phone, body)
    return _record_message(candidate, body, result, retry_of=retry_of)


@dataclass
class BulkSendResult:
    candidate_id: int
    message: Message | None = None
    error: str = ''

    @property
    def status(self):
        return self.message.status if self.message else MessageStatus.FAILED


def bulk_send(candidates, body, *, provider=None):
    """Send `body` to each candidate independently; one failure never stops the rest."""
    provider = provider or get_provider()
    results = []
    for candidate in candidates:
        try:
            message = send_message(candidate, body, provider=provider)
        except Exception:
            logger.exception('Failed to process bulk message for candidate %s', candidate.pk)
            results.append(BulkSendResult(
                candidate_id=candidate.pk,
                error='Internal error while processing this recipient; no message was recorded.',
            ))
        else:
            results.append(BulkSendResult(candidate_id=candidate.pk, message=message))
    return results


# Retries ---------------------------------------------------------------------


def retry_message(message_id, *, provider=None):
    """Create a new attempt for a retryable failed message, linked via `retry_of`."""
    with transaction.atomic():
        original = (
            Message.objects.select_for_update()
            .select_related('candidate')
            .get(pk=message_id)
        )
        if original.status != MessageStatus.FAILED:
            raise RetryNotAllowed(
                'not_failed',
                f'Only failed messages can be retried; this message is "{original.status}".',
            )
        if not original.is_retryable:
            raise RetryNotAllowed(
                'permanent_failure',
                f'This message failed permanently ({original.error_code}) and cannot be retried.',
            )
        existing_retry = Message.objects.filter(retry_of=original).first()
        if existing_retry is not None:
            raise RetryNotAllowed(
                'already_retried',
                f'This message was already retried as message {existing_retry.pk}.',
                retry_message_id=existing_retry.pk,
            )
        if original.attempt >= settings.MESSAGE_MAX_ATTEMPTS:
            raise RetryNotAllowed(
                'max_attempts_reached',
                f'Maximum of {settings.MESSAGE_MAX_ATTEMPTS} attempts reached.',
            )
        return send_message(original.candidate, original.body, retry_of=original, provider=provider)


# Provider status updates -----------------------------------------------------


def is_valid_transition(current, new):
    if current == MessageStatus.FAILED or current == new:
        return False
    if new == MessageStatus.FAILED:
        return current == MessageStatus.SENT
    return STATUS_RANK[new] > STATUS_RANK[current]


@dataclass
class StatusUpdateOutcome:
    result: str  # 'applied' or 'duplicate'
    message: Message
    event: MessageStatusEvent


def _existing_event_outcome(event_id, provider_message_id, status):
    event = (
        MessageStatusEvent.objects.select_related('message')
        .filter(provider_event_id=event_id)
        .first()
    )
    if event is None:
        return None
    if event.message.provider_message_id != provider_message_id or event.new_status != status:
        raise EventConflict(
            f'Event "{event_id}" was already received with different content.',
        )
    return StatusUpdateOutcome(result='duplicate', message=event.message, event=event)


def apply_status_update(
    *, event_id, provider_message_id, status, occurred_at,
    error_code='', failure_reason='', payload=None,
):
    """Apply a provider status event idempotently, rejecting regressions and invalid transitions."""
    with transaction.atomic():
        duplicate = _existing_event_outcome(event_id, provider_message_id, status)
        if duplicate is not None:
            return duplicate

        try:
            message = Message.objects.select_for_update().get(
                provider_message_id=provider_message_id
            )
        except Message.DoesNotExist:
            raise MessageNotFound(
                f'No message found with provider_message_id "{provider_message_id}".'
            ) from None

        previous = message.status
        if not is_valid_transition(previous, status):
            raise InvalidStatusTransition(
                f'Cannot change message status from "{previous}" to "{status}".',
                current_status=previous,
            )

        try:
            with transaction.atomic():
                event = MessageStatusEvent.objects.create(
                    message=message,
                    provider_event_id=event_id,
                    previous_status=previous,
                    new_status=status,
                    occurred_at=occurred_at,
                    payload=payload or {},
                )
        except IntegrityError:
            # A concurrent request stored the same event first.
            duplicate = _existing_event_outcome(event_id, provider_message_id, status)
            if duplicate is not None:
                return duplicate
            raise

        message.status = status
        update_fields = ['status', 'updated_at']
        if status == MessageStatus.FAILED:
            message.error_code = error_code or ErrorCode.DELIVERY_FAILED
            message.failure_reason = failure_reason or 'Provider reported a delivery failure.'
            message.is_retryable = is_retryable(message.error_code)
            update_fields += ['error_code', 'failure_reason', 'is_retryable']
        message.save(update_fields=update_fields)

    return StatusUpdateOutcome(result='applied', message=message, event=event)
