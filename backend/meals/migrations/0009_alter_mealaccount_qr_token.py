import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0008_populate_qr_tokens'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mealaccount',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
