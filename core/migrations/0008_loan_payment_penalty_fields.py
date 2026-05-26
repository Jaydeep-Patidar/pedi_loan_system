from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_payment_grace_days_used_and_completed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='loanpayment',
            name='base_amount_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='penalty_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='total_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='grace_days_used',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='payment_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='loantransaction',
            name='base_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='loantransaction',
            name='penalty_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
