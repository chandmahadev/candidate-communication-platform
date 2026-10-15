import secrets
import string

import django.db.models.deletion
from django.db import migrations, models


def backfill_codes(apps, schema_editor):
    Candidate = apps.get_model('candidates', 'Candidate')
    pools = (string.ascii_uppercase, string.digits)
    used = set()
    for candidate in Candidate.objects.all():
        while True:
            code = ''.join(secrets.choice(pools[i % 2]) for i in range(6))
            if code not in used:
                break
        used.add(code)
        candidate.code = code
        candidate.save(update_fields=['code'])


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0002_message_messagestatusevent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='code',
            field=models.CharField(editable=False, max_length=6, null=True),
        ),
        migrations.RunPython(backfill_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='candidate',
            name='code',
            field=models.CharField(editable=False, max_length=6, unique=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='candidate',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='messages',
                to='candidates.candidate',
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='retry_of',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='retry_attempt',
                to='candidates.message',
            ),
        ),
    ]
