"""Provider-agnostic types shared by all communication providers.

Nothing in this module depends on Django, so providers can be developed and
tested independently of the web layer.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


class ErrorCode:
    # Permanent: retrying the same request will not succeed.
    INVALID_RECIPIENT = 'invalid_recipient'
    BODY_REJECTED = 'body_rejected'
    # Temporary: the same request may succeed later.
    PROVIDER_UNAVAILABLE = 'provider_unavailable'
    RATE_LIMITED = 'rate_limited'
    PROVIDER_ERROR = 'provider_error'
    DELIVERY_FAILED = 'delivery_failed'


RETRYABLE_ERROR_CODES = frozenset({
    ErrorCode.PROVIDER_UNAVAILABLE,
    ErrorCode.RATE_LIMITED,
    ErrorCode.PROVIDER_ERROR,
    ErrorCode.DELIVERY_FAILED,
})

PERMANENT_ERROR_CODES = frozenset({
    ErrorCode.INVALID_RECIPIENT,
    ErrorCode.BODY_REJECTED,
})

ALL_ERROR_CODES = RETRYABLE_ERROR_CODES | PERMANENT_ERROR_CODES


def is_retryable(error_code):
    return error_code in RETRYABLE_ERROR_CODES


class DeliveryStatus:
    """Statuses a provider can report after a message has been accepted."""

    DELIVERED = 'delivered'
    READ = 'read'
    FAILED = 'failed'

    ALL = (DELIVERED, READ, FAILED)


@dataclass(frozen=True)
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error_code: str = ''
    error_message: str = ''
    retryable: bool = False

    @classmethod
    def ok(cls, provider_message_id):
        return cls(success=True, provider_message_id=provider_message_id)

    @classmethod
    def failure(cls, error_code, error_message):
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message,
            retryable=is_retryable(error_code),
        )


@dataclass(frozen=True)
class StatusUpdate:
    """A delivery-status event, shaped like the payload the provider posts to our webhook."""

    event_id: str
    provider_message_id: str
    status: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_code: str = ''
    failure_reason: str = ''

    def to_payload(self):
        payload = {
            'event_id': self.event_id,
            'provider_message_id': self.provider_message_id,
            'status': self.status,
            'timestamp': self.occurred_at.isoformat(),
        }
        if self.error_code:
            payload['error_code'] = self.error_code
        if self.failure_reason:
            payload['failure_reason'] = self.failure_reason
        return payload


class BaseProvider(ABC):
    name = 'base'

    @abstractmethod
    def send(self, recipient, body):
        """Send `body` to `recipient`. Must return a SendResult and never raise."""
