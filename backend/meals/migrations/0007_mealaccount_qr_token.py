import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0006_adminissue'),
    ]

    operations = [
        migrations.AddField(
            model_name='mealaccount',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
    ]
