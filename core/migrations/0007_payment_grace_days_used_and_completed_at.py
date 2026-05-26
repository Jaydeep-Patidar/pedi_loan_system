from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_payment_base_amount_paid_payment_penalty_paid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='grace_days_used',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
