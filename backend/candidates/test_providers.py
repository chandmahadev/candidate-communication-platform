from datetime import datetime, timezone
from unittest import mock

from django.test import SimpleTestCase, override_settings

from .providers import get_provider
from .providers.base import DeliveryStatus, ErrorCode, SendResult, is_retryable
from .providers.dummy import MAX_BODY_LENGTH, DummyProvider, Outcome

OK_PHONE = '+91 98765 43210'
PERMANENT_PHONE = '9876500000'
TEMPORARY_PHONE = '9876549999'
FLAKY_PHONE = '9876549998'


class DummyProviderSendTests(SimpleTestCase):
    def setUp(self):
        self.provider = DummyProvider()

    def test_success_returns_unique_reference(self):
        first = self.provider.send(OK_PHONE, 'Hello')
        second = self.provider.send(OK_PHONE, 'Hello')

        self.assertIsInstance(first, SendResult)
        self.assertTrue(first.success)
        self.assertTrue(first.provider_message_id.startswith('dummy_'))
        self.assertNotEqual(first.provider_message_id, second.provider_message_id)
        self.assertEqual(first.error_code, '')

    def test_permanent_failure_suffix(self):
        result = self.provider.send(PERMANENT_PHONE, 'Hello')

        self.assertFalse(result.success)
        self.assertIsNone(result.provider_message_id)
        self.assertEqual(result.error_code, ErrorCode.INVALID_RECIPIENT)
        self.assertFalse(result.retryable)
        self.assertTrue(result.error_message)

    def test_temporary_failure_suffix_fails_every_time(self):
        for _ in range(3):
            result = self.provider.send(TEMPORARY_PHONE, 'Hello')
            self.assertFalse(result.success)
            self.assertEqual(result.error_code, ErrorCode.PROVIDER_UNAVAILABLE)
            self.assertTrue(result.retryable)

    def test_flaky_suffix_fails_first_then_succeeds(self):
        first = self.provider.send(FLAKY_PHONE, 'Hello')
        second = self.provider.send(FLAKY_PHONE, 'Hello')

        self.assertFalse(first.success)
        self.assertTrue(first.retryable)
        self.assertTrue(second.success)

    def test_invalid_recipient_format(self):
        for recipient in ('', None, '12345', '1' * 16, 'not-a-number'):
            with self.subTest(recipient=recipient):
                result = self.provider.send(recipient, 'Hello')
                self.assertFalse(result.success)
                self.assertEqual(result.error_code, ErrorCode.INVALID_RECIPIENT)
                self.assertFalse(result.retryable)

    def test_rejects_blank_and_oversized_body(self):
        for body in ('', '   ', 'x' * (MAX_BODY_LENGTH + 1)):
            with self.subTest(length=len(body)):
                result = self.provider.send(OK_PHONE, body)
                self.assertFalse(result.success)
                self.assertEqual(result.error_code, ErrorCode.BODY_REJECTED)
                self.assertFalse(result.retryable)

    def test_scripted_outcomes_are_consumed_in_order(self):
        provider = DummyProvider(scripted_outcomes=[Outcome.TEMPORARY_FAILURE, 'permanent_failure'])
        provider.queue_outcomes(Outcome.SUCCESS)

        results = [provider.send(OK_PHONE, 'Hello') for _ in range(4)]

        self.assertEqual(results[0].error_code, ErrorCode.PROVIDER_UNAVAILABLE)
        self.assertEqual(results[1].error_code, ErrorCode.INVALID_RECIPIENT)
        self.assertTrue(results[2].success)
        self.assertTrue(results[3].success)  # falls back to recipient rules

    def test_unexpected_internal_error_is_returned_as_result(self):
        with mock.patch.object(self.provider, '_next_scripted', side_effect=RuntimeError('boom')):
            result = self.provider.send(OK_PHONE, 'Hello')

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, ErrorCode.PROVIDER_ERROR)
        self.assertTrue(result.retryable)
        self.assertIn('boom', result.error_message)

    def test_error_code_classification(self):
        self.assertTrue(is_retryable(ErrorCode.PROVIDER_UNAVAILABLE))
        self.assertTrue(is_retryable(ErrorCode.RATE_LIMITED))
        self.assertFalse(is_retryable(ErrorCode.INVALID_RECIPIENT))
        self.assertFalse(is_retryable(ErrorCode.BODY_REJECTED))


class DummyProviderStatusSimulationTests(SimpleTestCase):
    def setUp(self):
        self.provider = DummyProvider()

    def test_simulate_delivered_and_read_payloads(self):
        at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        delivered = self.provider.simulate_delivered('dummy_abc', occurred_at=at)
        read = self.provider.simulate_read('dummy_abc')

        self.assertEqual(delivered.status, DeliveryStatus.DELIVERED)
        self.assertEqual(read.status, DeliveryStatus.READ)
        self.assertNotEqual(delivered.event_id, read.event_id)
        self.assertEqual(
            delivered.to_payload(),
            {
                'event_id': delivered.event_id,
                'provider_message_id': 'dummy_abc',
                'status': 'delivered',
                'timestamp': '2026-01-01T12:00:00+00:00',
            },
        )

    def test_simulate_failed_includes_defaults(self):
        payload = self.provider.simulate_failed('dummy_abc').to_payload()

        self.assertEqual(payload['status'], 'failed')
        self.assertEqual(payload['error_code'], ErrorCode.DELIVERY_FAILED)
        self.assertTrue(payload['failure_reason'])

    def test_custom_event_id(self):
        update = self.provider.simulate_read('dummy_abc', event_id='evt_fixed')
        self.assertEqual(update.event_id, 'evt_fixed')

    def test_unsupported_status_raises(self):
        with self.assertRaises(ValueError):
            self.provider.simulate_status_update('dummy_abc', 'sent')


class GetProviderTests(SimpleTestCase):
    @override_settings(MESSAGING_PROVIDER='candidates.providers.dummy.DummyProvider')
    def test_returns_shared_configured_instance(self):
        first = get_provider()
        self.assertIsInstance(first, DummyProvider)
        self.assertIs(first, get_provider())
