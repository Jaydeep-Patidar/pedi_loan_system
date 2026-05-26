from datetime import date

from django.db import migrations, models


def backfill_payment_due_date(apps, schema_editor):
    Payment = apps.get_model('core', 'Payment')
    Pedi = apps.get_model('core', 'Pedi')

    # Backfill only when due_date is NULL (legacy rows)
    # Compute due_date using Pedi.monthly_due_day and payment month/year.
    # Assumption: monthly_due_day is now always valid (1..28) so day is safe.
    for payment in Payment.objects.filter(due_date__isnull=True).only('id', 'pedi_id', 'year', 'month'):
        pedi = Pedi.objects.filter(id=payment.pedi_id).only('monthly_due_day').first()
        if not pedi:
            continue
        due_day = getattr(pedi, 'monthly_due_day', 1) or 1
        due = date(payment.year, payment.month, due_day)
        Payment.objects.filter(id=payment.id).update(due_date=due)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_remove_loan_overdue_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedi',
            name='monthly_due_day',
            field=models.PositiveIntegerField(default=1),
        ),

        migrations.AddField(
            model_name='payment',
            name='due_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_payment_due_date, reverse_code=migrations.RunPython.noop),
    ]

