import secrets
import string

from django.db import models
from django.db.models.functions import Lower

CANDIDATE_CODE_LENGTH = 6


def generate_candidate_code():
    """Return a display ID such as "A1B2C3": alternating uppercase letters and digits."""
    pools = (string.ascii_uppercase, string.digits)
    return ''.join(secrets.choice(pools[i % 2]) for i in range(CANDIDATE_CODE_LENGTH))


def unique_candidate_code():
    while True:
        code = generate_candidate_code()
        if not Candidate.objects.filter(code=code).exists():
            return code


class Candidate(models.Model):
    code = models.CharField(max_length=CANDIDATE_CODE_LENGTH, unique=True, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='candidate_email_ci_unique',
                violation_error_message='A candidate with this email already exists.',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_candidate_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} <{self.email}>'


class MessageStatus(models.TextChoices):
    SENT = 'sent', 'Sent'
    DELIVERED = 'delivered', 'Delivered'
    READ = 'read', 'Read'
    FAILED = 'failed', 'Failed'


class Message(models.Model):
    # Deleting a candidate deletes their communication history.
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='messages')
    body = models.TextField()
    status = models.CharField(max_length=16, choices=MessageStatus.choices)
    provider_message_id = models.CharField(max_length=128, null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    failure_reason = models.TextField(blank=True)
    is_retryable = models.BooleanField(default=False)
    # RESTRICT (not PROTECT) so the chain can still be removed when the candidate is deleted.
    retry_of = models.OneToOneField(
        'self',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='retry_attempt',
    )
    attempt = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['candidate', '-created_at'], name='message_candidate_created_idx'),
            models.Index(fields=['status', '-created_at'], name='message_status_created_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['provider_message_id'],
                condition=models.Q(provider_message_id__isnull=False),
                name='message_provider_id_unique',
            ),
            models.CheckConstraint(
                condition=models.Q(status=MessageStatus.FAILED)
                | models.Q(provider_message_id__isnull=False),
                name='message_non_failed_has_provider_id',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=MessageStatus.FAILED) & ~models.Q(failure_reason='')
                ) | (
                    ~models.Q(status=MessageStatus.FAILED) & models.Q(failure_reason='')
                ),
                name='message_failure_reason_iff_failed',
            ),
            models.CheckConstraint(
                condition=models.Q(is_retryable=False) | models.Q(status=MessageStatus.FAILED),
                name='message_retryable_only_if_failed',
            ),
            models.CheckConstraint(
                condition=models.Q(attempt__gte=1),
                name='message_attempt_positive',
            ),
        ]

    def __str__(self):
        return f'Message {self.pk} to candidate {self.candidate_id} ({self.status})'


class MessageStatusEvent(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='status_events')
    provider_event_id = models.CharField(max_length=128, unique=True)
    previous_status = models.CharField(max_length=16, choices=MessageStatus.choices)
    new_status = models.CharField(max_length=16, choices=MessageStatus.choices)
    occurred_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['occurred_at', 'id']
        indexes = [
            models.Index(fields=['message', 'occurred_at'], name='status_event_message_time_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(previous_status=models.F('new_status')),
                name='status_event_changes_status',
            ),
        ]

    def __str__(self):
        return f'{self.provider_event_id}: {self.previous_status} -> {self.new_status}'
