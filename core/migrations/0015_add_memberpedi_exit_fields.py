from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_add_payment_is_cancelled'),
    ]

    operations = [
        migrations.AddField(
            model_name='memberpedi',
            name='exit_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='memberpedi',
            name='exit_reason',
            field=models.TextField(blank=True),
        ),
    ]
