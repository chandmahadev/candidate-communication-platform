from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Candidate, Message
from .serializers import (
    BulkDeleteCandidatesSerializer,
    BulkSendMessageSerializer,
    CandidateSerializer,
    MessageDetailSerializer,
    MessageFilterSerializer,
    MessageSerializer,
    SendMessageSerializer,
    StatusWebhookSerializer,
)


def candidates_with_last_message():
    latest = Message.objects.filter(candidate=OuterRef('pk')).order_by('-created_at', '-id')
    return Candidate.objects.annotate(
        last_message_at=Subquery(latest.values('created_at')[:1]),
        last_message_status=Subquery(latest.values('status')[:1]),
    )


class CandidateListCreateView(generics.ListCreateAPIView):
    """GET: list candidates (supports ?search=). POST: create a candidate."""

    serializer_class = CandidateSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'email', 'phone', 'code']

    def get_queryset(self):
        return candidates_with_last_message()


class CandidateDetailView(generics.RetrieveDestroyAPIView):
    """GET: retrieve a candidate. DELETE: remove the candidate and their communication history."""

    serializer_class = CandidateSerializer

    def get_queryset(self):
        return candidates_with_last_message()


class CandidateBulkDeleteView(APIView):
    """POST {"ids": [...]}: delete several candidates (and their history) in one transaction."""

    def post(self, request):
        serializer = BulkDeleteCandidatesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']
        with transaction.atomic():
            Candidate.objects.filter(pk__in=ids).delete()
        return Response({'deleted': len(ids)}, status=status.HTTP_200_OK)


# Messaging -------------------------------------------------------------------


def _error_response(exc, http_status):
    return Response({'detail': exc.detail, 'code': exc.code, **exc.extra}, status=http_status)


def _message_queryset():
    return Message.objects.select_related('candidate', 'retry_attempt')


class FilteredMessageListMixin:
    """Applies validated ?status= and ?candidate= filters to a message queryset."""

    serializer_class = MessageSerializer

    def filter_messages(self, queryset):
        params = MessageFilterSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        if 'status' in params.validated_data:
            queryset = queryset.filter(status=params.validated_data['status'])
        if 'candidate' in params.validated_data:
            queryset = queryset.filter(candidate_id=params.validated_data['candidate'])
        return queryset


class MessageListView(FilteredMessageListMixin, generics.ListAPIView):
    """GET: list messages, filterable by ?status= and ?candidate=."""

    def get_queryset(self):
        return self.filter_messages(_message_queryset())


class MessageDetailView(generics.RetrieveAPIView):
    """GET: a single message with its status-event history."""

    serializer_class = MessageDetailSerializer

    def get_queryset(self):
        return _message_queryset().prefetch_related('status_events')


class CandidateMessageListView(FilteredMessageListMixin, generics.ListAPIView):
    """GET: communication history for one candidate, filterable by ?status=."""

    def get_queryset(self):
        candidate = get_object_or_404(Candidate, pk=self.kwargs['pk'])
        return self.filter_messages(_message_queryset().filter(candidate=candidate))


class SendMessageView(APIView):
    """POST: send one message to a candidate."""

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = services.send_message(
            serializer.validated_data['candidate'], serializer.validated_data['body']
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class BulkSendMessageView(APIView):
    """POST: send the same body to several candidates, each as an independent message."""

    def post(self, request):
        serializer = BulkSendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = services.bulk_send(
            serializer.validated_data['candidates'], serializer.validated_data['body']
        )

        items = []
        for result in results:
            message = result.message
            items.append({
                'candidate_id': result.candidate_id,
                'message_id': message.pk if message else None,
                'status': result.status,
                'provider_message_id': message.provider_message_id if message else None,
                'error_code': message.error_code if message else 'internal_error',
                'failure_reason': message.failure_reason if message else result.error,
                'is_retryable': message.is_retryable if message else False,
            })
        sent = sum(1 for item in items if item['status'] != 'failed')
        return Response(
            {
                'summary': {'total': len(items), 'sent': sent, 'failed': len(items) - sent},
                'results': items,
            },
            status=status.HTTP_201_CREATED,
        )


class RetryMessageView(APIView):
    """POST: retry a failed message as a new linked message record."""

    def post(self, request, pk):
        get_object_or_404(Message, pk=pk)
        try:
            message = services.retry_message(pk)
        except services.RetryNotAllowed as exc:
            return _error_response(exc, status.HTTP_409_CONFLICT)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class ProviderStatusWebhookView(APIView):
    """POST: receive a delivery-status event from the communication provider."""

    authentication_classes = []

    def post(self, request):
        serializer = StatusWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            outcome = services.apply_status_update(
                event_id=data['event_id'],
                provider_message_id=data['provider_message_id'],
                status=data['status'],
                occurred_at=data['timestamp'],
                error_code=data.get('error_code', ''),
                failure_reason=data.get('failure_reason', ''),
                payload=request.data,
            )
        except services.MessageNotFound as exc:
            return _error_response(exc, status.HTTP_404_NOT_FOUND)
        except (services.InvalidStatusTransition, services.EventConflict) as exc:
            return _error_response(exc, status.HTTP_409_CONFLICT)

        return Response(
            {
                'result': outcome.result,
                'event_id': outcome.event.provider_event_id,
                'message': MessageSerializer(outcome.message).data,
            },
            status=status.HTTP_200_OK,
        )
