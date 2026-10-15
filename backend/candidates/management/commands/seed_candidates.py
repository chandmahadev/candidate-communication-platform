import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from candidates.models import Candidate, Message, MessageStatus, MessageStatusEvent
from candidates.providers.base import ErrorCode

LONG_1 = (
    'Great ideas often begin with simple observations. Creativity grows when we explore new '
    'perspectives and challenge familiar ways of thinking. Every small step brings us closer to '
    'meaningful progress. The key is to stay curious, embrace change, and keep moving forward.'
)
LONG_2 = (
    'The world is full of possibilities waiting to be explored. Every day brings new opportunities '
    'to learn, grow, and discover something unexpected. Sometimes, the smallest moments leave the '
    'biggest impressions on our lives. What truly matters is how we choose to make the most of them.'
)
LONG_3 = (
    'Every new experience brings an opportunity to learn something valuable. Even the smallest '
    'steps can lead to meaningful progress over time.'
)

# (name, phone, email, [(days_ago, hour, minute, final_status, body)])
CANDIDATES = [
    ('Krishna Khandelwal', '+91 9876543210', 'krishna.khandelwal@gmail.com', [
        (33, 22, 0, MessageStatus.READ, LONG_3),
        (26, 22, 0, MessageStatus.READ, LONG_2),
        (3, 10, 47, MessageStatus.READ, LONG_1),
    ]),
    ('Urvashi Soni', '+91 9123456789', 'urvashi.soni@gmail.com', [
        (6, 11, 15, MessageStatus.READ, 'Hi Urvashi, thanks for applying. We will be in touch soon.'),
        (2, 9, 30, MessageStatus.FAILED, 'Your interview is scheduled for Friday at 10 AM. Please confirm.'),
    ]),
    ('Aditya Kumar', '+91 9988766554', 'aditya.kumar@gmail.com', [
        (5, 14, 5, MessageStatus.READ, 'Hi Aditya, could you share your updated resume?'),
    ]),
    ('Ajit Srivastava', '+91 9234567890', 'ajit.srivastava@gmail.com', [
        (4, 16, 20, MessageStatus.READ, 'Your assessment link has been shared on your email.'),
    ]),
    ('Aniket Sawant', '+91 9876512345', 'aniket.sawant@gmail.com', [
        (2, 12, 0, MessageStatus.DELIVERED, 'Reminder: your interview is tomorrow at 11 AM.'),
        (1, 18, 45, MessageStatus.SENT, 'Please carry a government ID to the interview.'),
    ]),
    ('Ira Akbar', '+91 9456789012', 'ira.akbar@gmail.com', []),
    ('Amarjeet Kumar', '+91 9012345678', 'amarjeet.kumar@gmail.com', []),
]

PROGRESSION = [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]


class Command(BaseCommand):
    help = 'Seed the candidates and communication history shown in the Figma design.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete all existing candidates (and their messages) before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            Candidate.objects.all().delete()

        created = 0
        now = timezone.now()
        # Oldest first so the newest-first list matches the design order.
        for offset, (name, phone, email, messages) in enumerate(reversed(CANDIDATES)):
            if Candidate.objects.filter(email__iexact=email).exists():
                continue
            candidate = Candidate.objects.create(name=name, phone=phone, email=email)
            Candidate.objects.filter(pk=candidate.pk).update(
                created_at=now - timedelta(seconds=len(CANDIDATES) - offset)
            )
            for days_ago, hour, minute, final_status, body in messages:
                at = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                self._create_message(candidate, body, final_status, at)
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {created} candidate(s).'))

    def _create_message(self, candidate, body, final_status, at):
        if final_status == MessageStatus.FAILED:
            message = Message.objects.create(
                candidate=candidate, body=body, status=MessageStatus.FAILED,
                error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                failure_reason='Provider temporarily unavailable. Please retry later.',
                is_retryable=True,
            )
            Message.objects.filter(pk=message.pk).update(created_at=at, updated_at=at)
            return

        message = Message.objects.create(
            candidate=candidate, body=body, status=final_status,
            provider_message_id=f'seed_{uuid.uuid4().hex}', sent_at=at,
        )
        Message.objects.filter(pk=message.pk).update(created_at=at, updated_at=at)
        steps = PROGRESSION[: PROGRESSION.index(final_status) + 1]
        for index, (previous, new) in enumerate(zip(steps, steps[1:]), start=1):
            MessageStatusEvent.objects.create(
                message=message,
                provider_event_id=f'seed_{uuid.uuid4().hex}',
                previous_status=previous,
                new_status=new,
                occurred_at=at + timedelta(minutes=5 * index),
            )
