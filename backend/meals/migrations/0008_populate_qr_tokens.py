import uuid
from django.db import migrations


def assign_unique_qr_tokens(apps, schema_editor):
    """
    The previous migration's AddField gave every existing row the SAME
    evaluated default (Postgres evaluates a column default once per
    ADD COLUMN statement, not once per row) — so every MealAccount
    created before this migration currently shares one identical
    qr_token. Give each one its own real UUID before the next
    migration makes the column unique.
    """
    MealAccount = apps.get_model('meals', 'MealAccount')
    for account in MealAccount.objects.all():
        account.qr_token = uuid.uuid4()
        account.save(update_fields=['qr_token'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0007_mealaccount_qr_token'),
    ]

    operations = [
        migrations.RunPython(assign_unique_qr_tokens, noop_reverse),
    ]
