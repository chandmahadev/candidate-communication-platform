import re

from rest_framework import serializers

from .models import Candidate, Message, MessageStatus, MessageStatusEvent
from .providers.base import ALL_ERROR_CODES, DeliveryStatus

# Optional leading "+", then digits with optional spaces, hyphens, dots or parentheses.
PHONE_ALLOWED_CHARS = re.compile(r'^\+?[\d\s\-().]+$')
PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15  # E.164 maximum


class CandidateSerializer(serializers.ModelSerializer):
    # Populated by `with_last_message()`; None for candidates who were never messaged.
    last_message_at = serializers.SerializerMethodField()
    last_message_status = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'code', 'name', 'email', 'phone', 'last_message_at', 'last_message_status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']

    def get_last_message_at(self, obj):
        return getattr(obj, 'last_message_at', None)

    def get_last_message_status(self, obj):
        return getattr(obj, 'last_message_status', None)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Name may not be blank.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        duplicates = Candidate.objects.filter(email__iexact=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError('A candidate with this email already exists.')
        return value

    def validate_phone(self, value):
        value = value.strip()
        if not PHONE_ALLOWED_CHARS.match(value):
            raise serializers.ValidationError(
                'Phone may contain only digits, spaces, hyphens, dots, parentheses '
                'and an optional leading "+".'
            )
        digit_count = sum(ch.isdigit() for ch in value)
        if not PHONE_MIN_DIGITS <= digit_count <= PHONE_MAX_DIGITS:
            raise serializers.ValidationError(
                f'Phone must contain between {PHONE_MIN_DIGITS} and {PHONE_MAX_DIGITS} digits.'
            )
        return value


# Messaging -------------------------------------------------------------------

MESSAGE_BODY_MAX_LENGTH = 1600
BULK_SEND_MAX_RECIPIENTS = 500


class MessageStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageStatusEvent
        fields = ['id', 'provider_event_id', 'previous_status', 'new_status', 'occurred_at', 'received_at']
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    candidate_id = serializers.IntegerField(read_only=True)
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    retry_of_id = serializers.IntegerField(read_only=True)
    retried_by_id = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'candidate_id', 'candidate_name', 'body', 'status', 'provider_message_id',
            'error_code', 'failure_reason', 'is_retryable', 'attempt', 'retry_of_id',
            'retried_by_id', 'created_at', 'sent_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_retried_by_id(self, obj):
        try:
            return obj.retry_attempt.pk
        except Message.DoesNotExist:
            return None


class MessageDetailSerializer(MessageSerializer):
    status_events = MessageStatusEventSerializer(many=True, read_only=True)

    class Meta(MessageSerializer.Meta):
        fields = MessageSerializer.Meta.fields + ['status_events']
        read_only_fields = fields


def _message_body_field():
    return serializers.CharField(max_length=MESSAGE_BODY_MAX_LENGTH, trim_whitespace=True)


class SendMessageSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField(min_value=1)
    body = _message_body_field()

    def validate_candidate_id(self, value):
        try:
            self._candidate = Candidate.objects.get(pk=value)
        except Candidate.DoesNotExist:
            raise serializers.ValidationError(f'Candidate with id {value} does not exist.') from None
        return value

    def validate(self, attrs):
        attrs['candidate'] = self._candidate
        return attrs


class BulkSendMessageSerializer(serializers.Serializer):
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=BULK_SEND_MAX_RECIPIENTS,
        error_messages={'empty': 'At least one candidate id is required.'},
    )
    body = _message_body_field()

    def validate_candidate_ids(self, value):
        seen, duplicates = set(), []
        for candidate_id in value:
            if candidate_id in seen and candidate_id not in duplicates:
                duplicates.append(candidate_id)
            seen.add(candidate_id)
        if duplicates:
            raise serializers.ValidationError(
                f'Duplicate candidate ids are not allowed: {duplicates}.'
            )

        found = Candidate.objects.in_bulk(value)
        missing = [candidate_id for candidate_id in value if candidate_id not in found]
        if missing:
            raise serializers.ValidationError(f'Candidates not found: {missing}.')

        self._candidates = [found[candidate_id] for candidate_id in value]
        return value

    def validate(self, attrs):
        attrs['candidates'] = self._candidates
        return attrs


class BulkDeleteCandidatesSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        error_messages={'empty': 'At least one candidate id is required.'},
    )

    def validate_ids(self, value):
        unique_ids = list(dict.fromkeys(value))
        found = set(Candidate.objects.filter(pk__in=unique_ids).values_list('pk', flat=True))
        missing = [candidate_id for candidate_id in unique_ids if candidate_id not in found]
        if missing:
            raise serializers.ValidationError(f'Candidates not found: {missing}.')
        return unique_ids


class MessageFilterSerializer(serializers.Serializer):
    """Validates query parameters for message list endpoints."""

    status = serializers.ChoiceField(choices=MessageStatus.choices, required=False)
    candidate = serializers.IntegerField(min_value=1, required=False)


class StatusWebhookSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=128)
    provider_message_id = serializers.CharField(max_length=128)
    status = serializers.ChoiceField(choices=DeliveryStatus.ALL)
    timestamp = serializers.DateTimeField()
    error_code = serializers.ChoiceField(choices=sorted(ALL_ERROR_CODES), required=False)
    failure_reason = serializers.CharField(max_length=1000, required=False)

    def validate(self, attrs):
        if attrs['status'] != DeliveryStatus.FAILED and (
            attrs.get('error_code') or attrs.get('failure_reason')
        ):
            raise serializers.ValidationError(
                'error_code and failure_reason are only allowed when status is "failed".'
            )
        return attrs
