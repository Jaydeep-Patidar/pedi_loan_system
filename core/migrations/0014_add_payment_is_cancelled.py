from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_loanapplicationsettings_versioning'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='is_cancelled',
            field=models.BooleanField(default=False),
        ),
    ]
