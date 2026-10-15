from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Candidate

LIST_URL = reverse('candidates:candidate-list')


def detail_url(pk):
    return reverse('candidates:candidate-detail', args=[pk])


class CandidateModelTests(TestCase):
    def test_db_rejects_case_insensitive_duplicate_email(self):
        Candidate.objects.create(name='A', email='dup@example.com', phone='9876543210')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Candidate.objects.create(name='B', email='DUP@example.com', phone='9876543211')

    def test_timestamps_are_set(self):
        candidate = Candidate.objects.create(name='A', email='a@example.com', phone='9876543210')
        self.assertIsNotNone(candidate.created_at)
        self.assertIsNotNone(candidate.updated_at)


class CandidateCreateTests(APITestCase):
    def setUp(self):
        self.valid_payload = {
            'name': 'Asha Verma',
            'email': 'asha.verma@example.com',
            'phone': '+91 98765-43210',
        }

    def test_create_candidate_success(self):
        response = self.client.post(LIST_URL, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Candidate.objects.count(), 1)
        body = response.json()
        self.assertEqual(body['name'], 'Asha Verma')
        self.assertEqual(body['email'], 'asha.verma@example.com')
        self.assertEqual(body['phone'], '+91 98765-43210')
        for key in ('id', 'created_at', 'updated_at'):
            self.assertIn(key, body)

    def test_create_normalizes_email_and_trims_whitespace(self):
        payload = {**self.valid_payload, 'name': '  Asha  ', 'email': '  Asha.Verma@Example.COM '}
        response = self.client.post(LIST_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['name'], 'Asha')
        self.assertEqual(response.json()['email'], 'asha.verma@example.com')

    def test_read_only_fields_are_ignored(self):
        payload = {**self.valid_payload, 'id': 999, 'created_at': '2000-01-01T00:00:00Z'}
        response = self.client.post(LIST_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.json()['id'], 999)
        self.assertFalse(response.json()['created_at'].startswith('2000'))

    def test_duplicate_email_rejected(self):
        self.client.post(LIST_URL, self.valid_payload, format='json')
        payload = {**self.valid_payload, 'name': 'Someone Else', 'phone': '9123456789'}
        response = self.client.post(LIST_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.json())
        self.assertEqual(Candidate.objects.count(), 1)

    def test_duplicate_email_rejected_case_insensitively(self):
        self.client.post(LIST_URL, self.valid_payload, format='json')
        payload = {**self.valid_payload, 'email': 'ASHA.VERMA@EXAMPLE.COM'}
        response = self.client.post(LIST_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.json())
        self.assertEqual(Candidate.objects.count(), 1)

    def test_missing_required_fields(self):
        response = self.client.post(LIST_URL, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        body = response.json()
        for field in ('name', 'email', 'phone'):
            self.assertIn(field, body)
        self.assertEqual(Candidate.objects.count(), 0)

    def test_blank_fields_rejected(self):
        for field in ('name', 'email', 'phone'):
            with self.subTest(field=field):
                payload = {**self.valid_payload, field: ''}
                response = self.client.post(LIST_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())

    def test_whitespace_only_name_rejected(self):
        payload = {**self.valid_payload, 'name': '   '}
        response = self.client.post(LIST_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.json())

    def test_invalid_email_rejected(self):
        for bad_email in ('not-an-email', 'missing-at.example.com', 'user@', '@example.com'):
            with self.subTest(email=bad_email):
                payload = {**self.valid_payload, 'email': bad_email}
                response = self.client.post(LIST_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('email', response.json())

    def test_invalid_phone_rejected(self):
        bad_phones = [
            'abc1234567',        # letters
            '12345',             # too few digits
            '1234567890123456',  # too many digits (16)
            '98765#43210',       # disallowed character
            '91+9876543210',     # "+" not at start
        ]
        for bad_phone in bad_phones:
            with self.subTest(phone=bad_phone):
                payload = {**self.valid_payload, 'phone': bad_phone}
                response = self.client.post(LIST_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('phone', response.json())

    def test_valid_phone_formats_accepted(self):
        good_phones = ['9876543210', '+919876543210', '+1 (415) 555-0132', '022.2345.6789']
        for i, phone in enumerate(good_phones):
            with self.subTest(phone=phone):
                payload = {**self.valid_payload, 'email': f'user{i}@example.com', 'phone': phone}
                response = self.client.post(LIST_URL, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())


class CandidateListAndSearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.asha = Candidate.objects.create(
            name='Asha Verma', email='asha@example.com', phone='+91 98765 43210'
        )
        cls.rahul = Candidate.objects.create(
            name='Rahul Singh', email='rahul.singh@hunar.ai', phone='9123456789'
        )
        cls.meera = Candidate.objects.create(
            name='Meera Iyer', email='meera@example.org', phone='8001112222'
        )

    def _ids(self, response):
        return {item['id'] for item in response.json()}

    def test_list_returns_all_candidates(self):
        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)
        self.assertEqual(self._ids(response), {self.asha.id, self.rahul.id, self.meera.id})

    def test_list_is_newest_first(self):
        response = self.client.get(LIST_URL)

        self.assertEqual(
            [item['id'] for item in response.json()],
            [self.meera.id, self.rahul.id, self.asha.id],
        )

    def test_list_empty(self):
        Candidate.objects.all().delete()
        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_search_by_name_case_insensitive(self):
        response = self.client.get(LIST_URL, {'search': 'rAhUl'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._ids(response), {self.rahul.id})

    def test_search_by_email(self):
        response = self.client.get(LIST_URL, {'search': 'example.com'})

        self.assertEqual(self._ids(response), {self.asha.id})

    def test_search_by_email_domain_partial(self):
        response = self.client.get(LIST_URL, {'search': 'hunar.ai'})

        self.assertEqual(self._ids(response), {self.rahul.id})

    def test_search_by_phone(self):
        response = self.client.get(LIST_URL, {'search': '800111'})

        self.assertEqual(self._ids(response), {self.meera.id})

    def test_search_no_match(self):
        response = self.client.get(LIST_URL, {'search': 'nobody-here'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_empty_search_returns_all(self):
        response = self.client.get(LIST_URL, {'search': ''})

        self.assertEqual(len(response.json()), 3)


class CandidateDetailTests(APITestCase):
    def test_retrieve_existing_candidate(self):
        candidate = Candidate.objects.create(
            name='Asha Verma', email='asha@example.com', phone='9876543210'
        )
        response = self.client.get(detail_url(candidate.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body['id'], candidate.id)
        self.assertEqual(body['name'], 'Asha Verma')
        self.assertEqual(body['email'], 'asha@example.com')
        self.assertEqual(body['phone'], '9876543210')

    def test_retrieve_missing_candidate_returns_404(self):
        response = self.client.get(detail_url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.json())

    def test_non_integer_id_returns_404(self):
        response = self.client.get('/api/candidates/abc/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_does_not_allow_update_methods(self):
        candidate = Candidate.objects.create(
            name='Asha Verma', email='asha@example.com', phone='9876543210'
        )
        for method in ('put', 'patch'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(detail_url(candidate.id), {}, format='json')
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CandidateCodeAndLastMessageTests(APITestCase):
    def test_code_is_generated_unique_and_read_only(self):
        response = self.client.post(
            LIST_URL,
            {'name': 'A', 'email': 'a@example.com', 'phone': '9876543210', 'code': 'ZZZZZZ'},
            format='json',
        )
        code = response.json()['code']
        self.assertRegex(code, r'^[A-Z]\d[A-Z]\d[A-Z]\d$')
        other = Candidate.objects.create(name='B', email='b@example.com', phone='9876543211')
        self.assertNotEqual(other.code, code)

    def test_search_by_code(self):
        candidate = Candidate.objects.create(name='A', email='a@example.com', phone='9876543210')
        Candidate.objects.create(name='B', email='b@example.com', phone='9876543211')

        response = self.client.get(LIST_URL, {'search': candidate.code.lower()})

        self.assertEqual([item['id'] for item in response.json()], [candidate.id])

    def test_last_message_fields(self):
        from .models import Message, MessageStatus

        contacted = Candidate.objects.create(name='A', email='a@example.com', phone='9876543210')
        never = Candidate.objects.create(name='B', email='b@example.com', phone='9876543211')
        Message.objects.create(
            candidate=contacted, body='old', status=MessageStatus.SENT, provider_message_id='p1',
        )
        newest = Message.objects.create(
            candidate=contacted, body='new', status=MessageStatus.FAILED,
            error_code='invalid_recipient', failure_reason='Bad number',
        )

        rows = {item['id']: item for item in self.client.get(LIST_URL).json()}

        self.assertEqual(rows[contacted.id]['last_message_status'], 'failed')
        self.assertIsNotNone(rows[contacted.id]['last_message_at'])
        self.assertTrue(rows[contacted.id]['last_message_at'].startswith(newest.created_at.date().isoformat()))
        self.assertIsNone(rows[never.id]['last_message_status'])
        self.assertIsNone(rows[never.id]['last_message_at'])


class CandidateDeleteTests(APITestCase):
    def setUp(self):
        self.a = Candidate.objects.create(name='A', email='a@example.com', phone='9876543210')
        self.b = Candidate.objects.create(name='B', email='b@example.com', phone='9876543211')
        self.c = Candidate.objects.create(name='C', email='c@example.com', phone='9876543212')

    def test_delete_single_candidate(self):
        response = self.client.delete(detail_url(self.a.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Candidate.objects.filter(pk=self.a.id).exists())

    def test_delete_missing_candidate_returns_404(self):
        response = self.client.delete(detail_url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete(self):
        url = reverse('candidates:candidate-bulk-delete')
        response = self.client.post(url, {'ids': [self.a.id, self.b.id]}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'deleted': 2})
        self.assertEqual(list(Candidate.objects.values_list('pk', flat=True)), [self.c.id])

    def test_bulk_delete_is_all_or_nothing(self):
        url = reverse('candidates:candidate-bulk-delete')
        response = self.client.post(url, {'ids': [self.a.id, 999999]}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ids', response.json())
        self.assertEqual(Candidate.objects.count(), 3)

    def test_bulk_delete_requires_ids(self):
        url = reverse('candidates:candidate-bulk-delete')
        response = self.client.post(url, {'ids': []}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
