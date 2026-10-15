from datetime import timedelta
from unittest import mock

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from . import services
from .models import Candidate, Message, MessageStatus, MessageStatusEvent
from .providers.base import ErrorCode
from .providers.dummy import DummyProvider, Outcome

SEND_URL = reverse('messaging:message-send')
BULK_URL = reverse('messaging:message-bulk-send')
LIST_URL = reverse('messaging:message-list')
WEBHOOK_URL = reverse('provider-status-webhook')

OK_PHONE = '9876543210'
OK_PHONE_2 = '9123456789'
PERMANENT_PHONE = '9876500000'
TEMPORARY_PHONE = '9876549999'
FLAKY_PHONE = '9876549998'


def detail_url(pk):
    return reverse('messaging:message-detail', args=[pk])


def retry_url(pk):
    return reverse('messaging:message-retry', args=[pk])


def history_url(pk):
    return reverse('candidates:candidate-messages', args=[pk])


class MessagingTestCase(APITestCase):
    """Gives every test a fresh, deterministic provider instead of the shared one."""

    def setUp(self):
        self.provider = DummyProvider()
        patcher = mock.patch('candidates.services.get_provider', return_value=self.provider)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def make_candidate(name, phone, email=None):
        email = email or f'{name.lower().replace(" ", ".")}@example.com'
        return Candidate.objects.create(name=name, email=email, phone=phone)

    def send(self, candidate, body='Your interview is scheduled for tomorrow.'):
        return self.client.post(SEND_URL, {'candidate_id': candidate.id, 'body': body}, format='json')

    def post_status(self, provider_message_id, new_status, event_id=None, **extra):
        update = self.provider.simulate_status_update(
            provider_message_id, new_status, event_id=event_id, **extra
        )
        return self.client.post(WEBHOOK_URL, update.to_payload(), format='json')


class SendMessageTests(MessagingTestCase):
    def setUp(self):
        super().setUp()
        self.candidate = self.make_candidate('Asha Verma', OK_PHONE)

    def test_send_success(self):
        response = self.send(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body['status'], 'sent')
        self.assertEqual(body['candidate_id'], self.candidate.id)
        self.assertTrue(body['provider_message_id'].startswith('dummy_'))
        self.assertIsNotNone(body['sent_at'])
        self.assertEqual(body['failure_reason'], '')
        self.assertEqual(body['attempt'], 1)

        message = Message.objects.get()
        self.assertEqual(message.status, MessageStatus.SENT)
        self.assertEqual(message.body, 'Your interview is scheduled for tomorrow.')

    def test_body_is_trimmed(self):
        response = self.send(self.candidate, body='  Hello there  ')
        self.assertEqual(response.json()['body'], 'Hello there')

    def test_permanent_failure_is_recorded(self):
        candidate = self.make_candidate('Bad Number', PERMANENT_PHONE)
        response = self.send(candidate)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body['status'], 'failed')
        self.assertEqual(body['error_code'], ErrorCode.INVALID_RECIPIENT)
        self.assertTrue(body['failure_reason'])
        self.assertFalse(body['is_retryable'])
        self.assertIsNone(body['provider_message_id'])
        self.assertIsNone(body['sent_at'])
        self.assertEqual(Message.objects.get().status, MessageStatus.FAILED)

    def test_temporary_failure_is_retryable(self):
        candidate = self.make_candidate('Busy Network', TEMPORARY_PHONE)
        body = self.send(candidate).json()

        self.assertEqual(body['status'], 'failed')
        self.assertEqual(body['error_code'], ErrorCode.PROVIDER_UNAVAILABLE)
        self.assertTrue(body['is_retryable'])

    def test_provider_exception_is_handled_gracefully(self):
        with (
            mock.patch.object(self.provider, 'send', side_effect=ConnectionError('timeout')),
            self.assertLogs('candidates.services', level='ERROR'),
        ):
            response = self.send(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body['status'], 'failed')
        self.assertEqual(body['error_code'], ErrorCode.PROVIDER_ERROR)
        self.assertIn('timeout', body['failure_reason'])
        self.assertTrue(body['is_retryable'])

    def test_nonexistent_candidate_rejected(self):
        response = self.client.post(SEND_URL, {'candidate_id': 99999, 'body': 'Hi'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('candidate_id', response.json())
        self.assertEqual(Message.objects.count(), 0)

    def test_invalid_payloads_rejected(self):
        cases = {
            'missing body': ({'candidate_id': self.candidate.id}, 'body'),
            'empty body': ({'candidate_id': self.candidate.id, 'body': ''}, 'body'),
            'whitespace body': ({'candidate_id': self.candidate.id, 'body': '   '}, 'body'),
            'null body': ({'candidate_id': self.candidate.id, 'body': None}, 'body'),
            'too long body': ({'candidate_id': self.candidate.id, 'body': 'x' * 1601}, 'body'),
            'missing candidate': ({'body': 'Hi'}, 'candidate_id'),
            'non-integer candidate': ({'candidate_id': 'abc', 'body': 'Hi'}, 'candidate_id'),
            'zero candidate': ({'candidate_id': 0, 'body': 'Hi'}, 'candidate_id'),
        }
        for label, (payload, field) in cases.items():
            with self.subTest(label):
                response = self.client.post(SEND_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())
        self.assertEqual(Message.objects.count(), 0)

    def test_each_send_creates_separate_message(self):
        first = self.send(self.candidate).json()
        second = self.send(self.candidate).json()

        self.assertNotEqual(first['id'], second['id'])
        self.assertNotEqual(first['provider_message_id'], second['provider_message_id'])
        self.assertEqual(Message.objects.count(), 2)


class BulkSendTests(MessagingTestCase):
    def setUp(self):
        super().setUp()
        self.ok = self.make_candidate('Asha Verma', OK_PHONE)
        self.ok2 = self.make_candidate('Rahul Singh', OK_PHONE_2)
        self.permanent = self.make_candidate('Bad Number', PERMANENT_PHONE)
        self.temporary = self.make_candidate('Busy Network', TEMPORARY_PHONE)

    def bulk(self, ids, body='Interview tomorrow at 10am.'):
        return self.client.post(BULK_URL, {'candidate_ids': ids, 'body': body}, format='json')

    def test_mixed_success_and_failure(self):
        ids = [self.ok.id, self.permanent.id, self.temporary.id, self.ok2.id]
        response = self.bulk(ids)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body['summary'], {'total': 4, 'sent': 2, 'failed': 2})
        results = body['results']
        self.assertEqual([r['candidate_id'] for r in results], ids)
        self.assertEqual([r['status'] for r in results], ['sent', 'failed', 'failed', 'sent'])
        self.assertEqual(results[1]['error_code'], ErrorCode.INVALID_RECIPIENT)
        self.assertFalse(results[1]['is_retryable'])
        self.assertEqual(results[2]['error_code'], ErrorCode.PROVIDER_UNAVAILABLE)
        self.assertTrue(results[2]['is_retryable'])
        for result in results:
            self.assertTrue(Message.objects.filter(pk=result['message_id']).exists())
        self.assertEqual(Message.objects.count(), 4)

    def test_first_failure_does_not_stop_remaining_recipients(self):
        response = self.bulk([self.permanent.id, self.ok.id, self.ok2.id])

        statuses = [r['status'] for r in response.json()['results']]
        self.assertEqual(statuses, ['failed', 'sent', 'sent'])
        self.assertEqual(Message.objects.filter(status=MessageStatus.SENT).count(), 2)

    def test_provider_exception_for_one_recipient_does_not_stop_others(self):
        real_send = self.provider.send

        def flaky_send(recipient, body):
            if recipient == OK_PHONE:
                raise RuntimeError('provider crashed')
            return real_send(recipient, body)

        with (
            mock.patch.object(self.provider, 'send', side_effect=flaky_send),
            self.assertLogs('candidates.services', level='ERROR'),
        ):
            response = self.bulk([self.ok.id, self.ok2.id])

        results = response.json()['results']
        self.assertEqual(results[0]['status'], 'failed')
        self.assertEqual(results[0]['error_code'], ErrorCode.PROVIDER_ERROR)
        self.assertEqual(results[1]['status'], 'sent')
        self.assertEqual(Message.objects.count(), 2)

    def test_database_error_for_one_recipient_keeps_other_messages(self):
        real_record = services._record_message

        def failing_record(candidate, *args, **kwargs):
            if candidate.pk == self.ok.pk:
                raise IntegrityError('simulated database failure')
            return real_record(candidate, *args, **kwargs)

        with (
            mock.patch('candidates.services._record_message', side_effect=failing_record),
            self.assertLogs('candidates.services', level='ERROR'),
        ):
            response = self.bulk([self.ok2.id, self.ok.id, self.permanent.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        results = response.json()['results']
        self.assertEqual(results[0]['status'], 'sent')
        self.assertIsNone(results[1]['message_id'])
        self.assertEqual(results[1]['status'], 'failed')
        self.assertEqual(results[1]['error_code'], 'internal_error')
        self.assertEqual(results[2]['status'], 'failed')
        self.assertEqual(response.json()['summary'], {'total': 3, 'sent': 1, 'failed': 2})
        self.assertEqual(
            set(Message.objects.values_list('candidate_id', flat=True)),
            {self.ok2.id, self.permanent.id},
        )

    def test_empty_recipient_list_rejected(self):
        response = self.bulk([])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('candidate_ids', response.json())

    def test_duplicate_candidate_ids_rejected(self):
        response = self.bulk([self.ok.id, self.ok2.id, self.ok.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Duplicate', response.json()['candidate_ids'][0])
        self.assertIn(str(self.ok.id), response.json()['candidate_ids'][0])
        self.assertEqual(Message.objects.count(), 0)

    def test_nonexistent_candidate_ids_rejected(self):
        response = self.bulk([self.ok.id, 99998, 99999])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = response.json()['candidate_ids'][0]
        self.assertIn('99998', error)
        self.assertIn('99999', error)
        self.assertEqual(Message.objects.count(), 0)

    def test_invalid_bulk_payloads_rejected(self):
        cases = {
            'missing ids': ({'body': 'Hi'}, 'candidate_ids'),
            'ids not a list': ({'candidate_ids': 'abc', 'body': 'Hi'}, 'candidate_ids'),
            'non-integer id': ({'candidate_ids': ['x'], 'body': 'Hi'}, 'candidate_ids'),
            'missing body': ({'candidate_ids': [self.ok.id]}, 'body'),
            'blank body': ({'candidate_ids': [self.ok.id], 'body': '  '}, 'body'),
        }
        for label, (payload, field) in cases.items():
            with self.subTest(label):
                response = self.client.post(BULK_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())
        self.assertEqual(Message.objects.count(), 0)


class StatusWebhookTests(MessagingTestCase):
    def setUp(self):
        super().setUp()
        self.candidate = self.make_candidate('Asha Verma', OK_PHONE)
        self.message = Message.objects.get(pk=self.send(self.candidate).json()['id'])
        self.pmid = self.message.provider_message_id

    def test_sent_to_delivered_to_read(self):
        delivered = self.post_status(self.pmid, 'delivered')
        self.assertEqual(delivered.status_code, status.HTTP_200_OK)
        self.assertEqual(delivered.json()['result'], 'applied')
        self.assertEqual(delivered.json()['message']['status'], 'delivered')

        read = self.post_status(self.pmid, 'read')
        self.assertEqual(read.status_code, status.HTTP_200_OK)
        self.assertEqual(read.json()['message']['status'], 'read')

        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.READ)
        events = list(self.message.status_events.values_list('previous_status', 'new_status'))
        self.assertEqual(events, [('sent', 'delivered'), ('delivered', 'read')])

        detail = self.client.get(detail_url(self.message.id)).json()
        self.assertEqual([e['new_status'] for e in detail['status_events']], ['delivered', 'read'])

    def test_sent_directly_to_read_is_allowed(self):
        response = self.post_status(self.pmid, 'read')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.READ)

    def test_duplicate_event_is_idempotent(self):
        update = self.provider.simulate_delivered(self.pmid)
        first = self.client.post(WEBHOOK_URL, update.to_payload(), format='json')
        second = self.client.post(WEBHOOK_URL, update.to_payload(), format='json')

        self.assertEqual(first.json()['result'], 'applied')
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.json()['result'], 'duplicate')
        self.assertEqual(MessageStatusEvent.objects.count(), 1)

    def test_replayed_old_event_after_newer_status_is_duplicate_not_regression(self):
        delivered = self.provider.simulate_delivered(self.pmid)
        self.client.post(WEBHOOK_URL, delivered.to_payload(), format='json')
        self.post_status(self.pmid, 'read')

        replay = self.client.post(WEBHOOK_URL, delivered.to_payload(), format='json')

        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.json()['result'], 'duplicate')
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.READ)
        self.assertEqual(MessageStatusEvent.objects.count(), 2)

    def test_reused_event_id_with_different_content_conflicts(self):
        self.post_status(self.pmid, 'delivered', event_id='evt_1')
        response = self.post_status(self.pmid, 'read', event_id='evt_1')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['code'], 'event_id_conflict')
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.DELIVERED)

    def test_out_of_order_update_cannot_regress_status(self):
        self.post_status(self.pmid, 'read')
        response = self.post_status(self.pmid, 'delivered')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        body = response.json()
        self.assertEqual(body['code'], 'invalid_status_transition')
        self.assertEqual(body['current_status'], 'read')
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.READ)
        self.assertEqual(MessageStatusEvent.objects.count(), 1)

    def test_repeated_same_status_with_new_event_id_is_rejected(self):
        self.post_status(self.pmid, 'delivered')
        response = self.post_status(self.pmid, 'delivered')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(MessageStatusEvent.objects.count(), 1)

    def test_delivery_failure_after_sent(self):
        response = self.post_status(self.pmid, 'failed')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.FAILED)
        self.assertEqual(self.message.error_code, ErrorCode.DELIVERY_FAILED)
        self.assertTrue(self.message.failure_reason)
        self.assertTrue(self.message.is_retryable)

    def test_permanent_delivery_failure_is_not_retryable(self):
        self.post_status(
            self.pmid, 'failed',
            error_code=ErrorCode.INVALID_RECIPIENT, failure_reason='Number disconnected',
        )
        self.message.refresh_from_db()
        self.assertFalse(self.message.is_retryable)
        self.assertEqual(self.message.failure_reason, 'Number disconnected')

    def test_failed_after_delivered_is_rejected(self):
        self.post_status(self.pmid, 'delivered')
        response = self.post_status(self.pmid, 'failed')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.DELIVERED)

    def test_no_updates_after_failed(self):
        self.post_status(self.pmid, 'failed')
        for new_status in ('delivered', 'read'):
            with self.subTest(new_status):
                response = self.post_status(self.pmid, new_status)
                self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.FAILED)

    def test_unknown_provider_message_id_returns_404(self):
        response = self.post_status('dummy_does_not_exist', 'delivered')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['code'], 'message_not_found')
        self.assertEqual(MessageStatusEvent.objects.count(), 0)

    def test_invalid_payloads_rejected(self):
        valid = self.provider.simulate_delivered(self.pmid).to_payload()
        cases = {
            'unknown status': ({**valid, 'status': 'bogus'}, 'status'),
            'sent is not an update': ({**valid, 'status': 'sent'}, 'status'),
            'missing event id': ({k: v for k, v in valid.items() if k != 'event_id'}, 'event_id'),
            'missing message id': (
                {k: v for k, v in valid.items() if k != 'provider_message_id'}, 'provider_message_id',
            ),
            'missing timestamp': ({k: v for k, v in valid.items() if k != 'timestamp'}, 'timestamp'),
            'bad timestamp': ({**valid, 'timestamp': 'yesterday'}, 'timestamp'),
            'unknown error code': ({**valid, 'status': 'failed', 'error_code': 'nope'}, 'error_code'),
            'error on non-failed status': (
                {**valid, 'error_code': ErrorCode.DELIVERY_FAILED}, 'non_field_errors',
            ),
        }
        for label, (payload, field) in cases.items():
            with self.subTest(label):
                response = self.client.post(WEBHOOK_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, MessageStatus.SENT)
        self.assertEqual(MessageStatusEvent.objects.count(), 0)

    def test_event_timestamp_is_stored(self):
        at = timezone.now() - timedelta(minutes=5)
        update = self.provider.simulate_delivered(self.pmid, occurred_at=at)
        self.client.post(WEBHOOK_URL, update.to_payload(), format='json')

        self.assertEqual(MessageStatusEvent.objects.get().occurred_at, at)


class MessageListAndDetailTests(MessagingTestCase):
    def setUp(self):
        super().setUp()
        self.asha = self.make_candidate('Asha Verma', OK_PHONE)
        self.bad = self.make_candidate('Bad Number', PERMANENT_PHONE)
        self.sent = Message.objects.get(pk=self.send(self.asha).json()['id'])
        self.failed = Message.objects.get(pk=self.send(self.bad).json()['id'])

    def test_list_all_newest_first(self):
        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([m['id'] for m in response.json()], [self.failed.id, self.sent.id])

    def test_filter_by_status(self):
        response = self.client.get(LIST_URL, {'status': 'failed'})
        self.assertEqual([m['id'] for m in response.json()], [self.failed.id])

    def test_filter_by_candidate(self):
        response = self.client.get(LIST_URL, {'candidate': self.asha.id})
        self.assertEqual([m['id'] for m in response.json()], [self.sent.id])

    def test_combined_filters(self):
        response = self.client.get(LIST_URL, {'candidate': self.asha.id, 'status': 'failed'})
        self.assertEqual(response.json(), [])

    def test_invalid_filters_rejected(self):
        for params, field in (({'status': 'bogus'}, 'status'), ({'candidate': 'abc'}, 'candidate')):
            with self.subTest(params=params):
                response = self.client.get(LIST_URL, params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())

    def test_detail(self):
        response = self.client.get(detail_url(self.sent.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body['id'], self.sent.id)
        self.assertEqual(body['candidate_name'], 'Asha Verma')
        self.assertEqual(body['status_events'], [])

    def test_detail_missing_returns_404(self):
        self.assertEqual(self.client.get(detail_url(99999)).status_code, status.HTTP_404_NOT_FOUND)


class CandidateHistoryTests(MessagingTestCase):
    def setUp(self):
        super().setUp()
        self.asha = self.make_candidate('Asha Verma', OK_PHONE)
        self.rahul = self.make_candidate('Rahul Singh', OK_PHONE_2)
        self.first = self.send(self.asha, 'First').json()['id']
        self.send(self.rahul, 'Other candidate')
        self.second = self.send(self.asha, 'Second').json()['id']

    def test_history_contains_only_that_candidate_newest_first(self):
        response = self.client.get(history_url(self.asha.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual([m['id'] for m in body], [self.second, self.first])
        self.assertEqual([m['body'] for m in body], ['Second', 'First'])

    def test_history_includes_status_updates_and_failures(self):
        provider_id = Message.objects.get(pk=self.first).provider_message_id
        self.post_status(provider_id, 'delivered')

        statuses = {m['id']: m['status'] for m in self.client.get(history_url(self.asha.id)).json()}
        self.assertEqual(statuses, {self.first: 'delivered', self.second: 'sent'})

    def test_history_status_filter(self):
        provider_id = Message.objects.get(pk=self.first).provider_message_id
        self.post_status(provider_id, 'read')

        response = self.client.get(history_url(self.asha.id), {'status': 'read'})
        self.assertEqual([m['id'] for m in response.json()], [self.first])

    def test_candidate_without_messages(self):
        quiet = self.make_candidate('Meera Iyer', '8001112222')
        response = self.client.get(history_url(quiet.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_missing_candidate_returns_404(self):
        self.assertEqual(self.client.get(history_url(99999)).status_code, status.HTTP_404_NOT_FOUND)


class RetryTests(MessagingTestCase):
    def test_retry_temporary_failure_succeeds_with_new_linked_message(self):
        candidate = self.make_candidate('Asha Verma', OK_PHONE)
        self.provider.queue_outcomes(Outcome.TEMPORARY_FAILURE)
        original = self.send(candidate).json()
        self.assertEqual(original['status'], 'failed')

        response = self.client.post(retry_url(original['id']))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        retry = response.json()
        self.assertNotEqual(retry['id'], original['id'])
        self.assertEqual(retry['status'], 'sent')
        self.assertEqual(retry['retry_of_id'], original['id'])
        self.assertEqual(retry['attempt'], 2)
        self.assertEqual(retry['body'], original['body'])

        original_now = self.client.get(detail_url(original['id'])).json()
        self.assertEqual(original_now['status'], 'failed')
        self.assertEqual(original_now['failure_reason'], original['failure_reason'])
        self.assertEqual(original_now['retried_by_id'], retry['id'])
        self.assertEqual(len(self.client.get(history_url(candidate.id)).json()), 2)

    def test_retry_flaky_recipient(self):
        candidate = self.make_candidate('Flaky Line', FLAKY_PHONE)
        original = self.send(candidate).json()

        response = self.client.post(retry_url(original['id']))

        self.assertEqual(original['status'], 'failed')
        self.assertEqual(response.json()['status'], 'sent')

    def test_permanent_failure_cannot_be_retried(self):
        candidate = self.make_candidate('Bad Number', PERMANENT_PHONE)
        original = self.send(candidate).json()

        response = self.client.post(retry_url(original['id']))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['code'], 'permanent_failure')
        self.assertEqual(Message.objects.count(), 1)

    def test_non_failed_message_cannot_be_retried(self):
        candidate = self.make_candidate('Asha Verma', OK_PHONE)
        original = self.send(candidate).json()

        response = self.client.post(retry_url(original['id']))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['code'], 'not_failed')
        self.assertEqual(Message.objects.count(), 1)

    def test_same_failure_cannot_be_retried_twice(self):
        candidate = self.make_candidate('Busy Network', TEMPORARY_PHONE)
        original = self.send(candidate).json()
        first_retry = self.client.post(retry_url(original['id'])).json()

        response = self.client.post(retry_url(original['id']))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['code'], 'already_retried')
        self.assertEqual(response.json()['retry_message_id'], first_retry['id'])
        self.assertEqual(Message.objects.count(), 2)

    @override_settings(MESSAGE_MAX_ATTEMPTS=3)
    def test_retry_chain_stops_at_max_attempts(self):
        candidate = self.make_candidate('Busy Network', TEMPORARY_PHONE)
        attempt_1 = self.send(candidate).json()
        attempt_2 = self.client.post(retry_url(attempt_1['id'])).json()
        attempt_3 = self.client.post(retry_url(attempt_2['id'])).json()

        response = self.client.post(retry_url(attempt_3['id']))

        self.assertEqual([attempt_2['attempt'], attempt_3['attempt']], [2, 3])
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['code'], 'max_attempts_reached')

    def test_retry_after_delivery_failure_webhook(self):
        candidate = self.make_candidate('Asha Verma', OK_PHONE)
        original = self.send(candidate).json()
        self.post_status(original['provider_message_id'], 'failed')

        response = self.client.post(retry_url(original['id']))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['status'], 'sent')

    def test_retry_missing_message_returns_404(self):
        self.assertEqual(self.client.post(retry_url(99999)).status_code, status.HTTP_404_NOT_FOUND)


class MessageConstraintTests(TestCase):
    def setUp(self):
        self.candidate = Candidate.objects.create(name='A', email='a@example.com', phone=OK_PHONE)

    def assert_integrity_error(self, **fields):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Message.objects.create(candidate=self.candidate, body='Hi', **fields)

    def test_sent_message_requires_provider_id(self):
        self.assert_integrity_error(status=MessageStatus.SENT)

    def test_failed_message_requires_failure_reason(self):
        self.assert_integrity_error(status=MessageStatus.FAILED)

    def test_non_failed_message_cannot_have_failure_reason(self):
        self.assert_integrity_error(
            status=MessageStatus.SENT, provider_message_id='p1', failure_reason='oops',
        )

    def test_only_failed_messages_are_retryable(self):
        self.assert_integrity_error(
            status=MessageStatus.SENT, provider_message_id='p1', is_retryable=True,
        )

    def test_provider_message_id_is_unique(self):
        Message.objects.create(
            candidate=self.candidate, body='Hi', status=MessageStatus.SENT, provider_message_id='p1',
        )
        self.assert_integrity_error(status=MessageStatus.SENT, provider_message_id='p1')

    def test_multiple_failed_messages_without_provider_id_allowed(self):
        for _ in range(2):
            Message.objects.create(
                candidate=self.candidate, body='Hi', status=MessageStatus.FAILED, failure_reason='x',
            )
        self.assertEqual(Message.objects.count(), 2)

    def test_status_event_id_unique_and_must_change_status(self):
        message = Message.objects.create(
            candidate=self.candidate, body='Hi', status=MessageStatus.SENT, provider_message_id='p1',
        )
        now = timezone.now()
        MessageStatusEvent.objects.create(
            message=message, provider_event_id='e1', previous_status='sent',
            new_status='delivered', occurred_at=now,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            MessageStatusEvent.objects.create(
                message=message, provider_event_id='e1', previous_status='delivered',
                new_status='read', occurred_at=now,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            MessageStatusEvent.objects.create(
                message=message, provider_event_id='e2', previous_status='read',
                new_status='read', occurred_at=now,
            )

    def test_deleting_candidate_deletes_history_including_retry_chains(self):
        original = Message.objects.create(
            candidate=self.candidate, body='Hi', status=MessageStatus.FAILED,
            error_code='provider_unavailable', failure_reason='Down', is_retryable=True,
        )
        retry = Message.objects.create(
            candidate=self.candidate, body='Hi', status=MessageStatus.SENT, provider_message_id='p1',
            retry_of=original, attempt=2,
        )
        MessageStatusEvent.objects.create(
            message=retry, provider_event_id='e1', previous_status='sent',
            new_status='delivered', occurred_at=timezone.now(),
        )

        self.candidate.delete()

        self.assertFalse(Message.objects.exists())
        self.assertFalse(MessageStatusEvent.objects.exists())

    def test_original_message_with_retry_cannot_be_deleted_on_its_own(self):
        from django.db.models import RestrictedError

        original = Message.objects.create(
            candidate=self.candidate, body='Hi', status=MessageStatus.FAILED,
            error_code='provider_unavailable', failure_reason='Down', is_retryable=True,
        )
        Message.objects.create(
            candidate=self.candidate, body='Hi', status=MessageStatus.SENT, provider_message_id='p1',
            retry_of=original, attempt=2,
        )
        with self.assertRaises(RestrictedError):
            original.delete()
