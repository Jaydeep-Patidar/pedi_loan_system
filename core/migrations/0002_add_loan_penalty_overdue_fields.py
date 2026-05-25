from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='overdue_days',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='loan',
            name='penalty_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='loan',
            name='penalty_status',
            field=models.CharField(choices=[('None', 'None'), ('Overdue', 'Overdue')], default='None', max_length=20),
        ),
    ]

