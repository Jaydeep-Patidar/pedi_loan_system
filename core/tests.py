from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Member, Pedi, Payment
from .utils_payment import complete_payment, get_payment_breakdown


class PaymentPenaltyTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='member1', password='pass')
        self.member = Member.objects.create(
            user=user,
            email='m@test.com',
            phone='9999999999',
            role='member',
        )
        self.pedi = Pedi.objects.create(
            name='Test Pedi',
            duration_months=12,
            monthly_amount=Decimal('200.00'),
            monthly_due_day=10,
            start_date=date(2025, 1, 1),
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )
        due = date(2025, 1, 10)
        self.payment = Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=1,
            year=2025,
            amount=Decimal('200.00'),
            due_date=due,
            status='Pending',
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )

    def test_future_payment_has_no_penalty(self):
        future = Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=12,
            year=2030,
            amount=Decimal('200.00'),
            due_date=date(2030, 12, 10),
            status='Pending',
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )
        self.assertEqual(future.calculate_penalty(), Decimal('0.00'))
        self.assertEqual(future.get_effective_overdue_status(), 'Pending')

    def test_complete_payment_freezes_penalty(self):
        today = self.payment.get_due_date_exact() + timedelta(days=self.payment.grace_days + 5)
        penalty = self.payment.calculate_penalty(today=today)
        self.assertEqual(penalty, Decimal('4.00'))

        complete_payment(self.payment, payment_method='Cash', transaction_id='TEST-1')
        self.payment.refresh_from_db()

        self.assertEqual(self.payment.status, 'Paid')
        self.assertEqual(self.payment.penalty_paid, Decimal('4.00'))
        self.assertEqual(self.payment.total_paid, Decimal('204.00'))
        self.assertEqual(self.payment.grace_days_used, 10)
        # Penalty must not change after payment even if time passes
        self.assertEqual(self.payment.calculate_penalty(), Decimal('4.00'))

    def test_breakdown_for_unpaid_includes_penalty_in_total(self):
        today = self.payment.get_due_date_exact() + timedelta(days=self.payment.grace_days + 1)
        breakdown = get_payment_breakdown(self.payment, today=today)
        self.assertEqual(breakdown['final_payable'], breakdown['base_amount'] + breakdown['penalty_amount'])
