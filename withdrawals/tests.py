from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import Member, Pedi, Payment, MemberPedi
from withdrawals.models import Withdrawal
from withdrawals.services import calculate_withdrawal_amount, can_member_withdraw


class WithdrawalCalculationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='wmember', password='pass')
        self.member = Member.objects.create(
            user=user,
            email='w@test.com',
            phone='8888888888',
            role='member',
        )
        self.pedi = Pedi.objects.create(
            name='Withdraw Pedi',
            duration_months=12,
            monthly_amount=Decimal('200.00'),
            monthly_due_day=10,
            start_date=date(2025, 1, 1),
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )
        MemberPedi.objects.create(
            member=self.member,
            pedi=self.pedi,
            status='Exited',
            membership_start_date=date(2025, 1, 1),
        )

    def _paid_payment(self, month, year, base=200, penalty=0):
        total = Decimal(base) + Decimal(penalty)
        return Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=month,
            year=year,
            amount=Decimal(str(base)),
            due_date=date(year, month, 10),
            status='Paid',
            base_amount_paid=Decimal(str(base)),
            penalty_paid=Decimal(str(penalty)),
            total_paid=total,
            payment_date=timezone.now(),
            payment_completed_at=timezone.now(),
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )

    def test_withdrawable_uses_contribution_not_penalty_paid(self):
        self._paid_payment(1, 2025, base=200, penalty=4)
        calc = calculate_withdrawal_amount(self.member)
        self.assertEqual(calc['total_contribution_paid'], Decimal('200.00'))
        self.assertEqual(calc['penalties_already_paid'], Decimal('4.00'))
        self.assertEqual(calc['withdrawable_amount'], Decimal('200.00'))

    def test_unpaid_overdue_penalty_reduces_withdrawable(self):
        self._paid_payment(1, 2025, base=200, penalty=0)
        overdue_due = date(2024, 1, 10)
        Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=2,
            year=2024,
            amount=Decimal('200.00'),
            due_date=overdue_due,
            status='Pending',
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )
        calc = calculate_withdrawal_amount(self.member)
        self.assertEqual(calc['unpaid_penalties_due'], Decimal('4.00'))
        self.assertEqual(calc['withdrawable_amount'], Decimal('196.00'))

    def test_future_pending_has_no_penalty(self):
        self._paid_payment(1, 2025)
        future_year = timezone.now().year + 2
        Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=6,
            year=future_year,
            amount=Decimal('200.00'),
            due_date=date(future_year, 6, 10),
            status='Pending',
            penalty_enabled=True,
            grace_days=10,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('4.00'),
        )
        calc = calculate_withdrawal_amount(self.member)
        self.assertEqual(calc['unpaid_penalties_due'], Decimal('0.00'))
        self.assertEqual(calc['withdrawable_amount'], Decimal('200.00'))

    def test_since_last_withdrawal_excludes_earlier_contributions(self):
        self._paid_payment(1, 2025)
        Withdrawal.objects.create(
            member=self.member,
            total_paid_amount=Decimal('200.00'),
            total_penalties_paid=Decimal('0.00'),
            withdrawal_amount=Decimal('200.00'),
            status='Completed',
            processed_at=timezone.now(),
        )
        self._paid_payment(2, 2025)
        calc = calculate_withdrawal_amount(self.member)
        self.assertEqual(calc['total_contribution_paid'], Decimal('200.00'))
        self.assertEqual(calc['withdrawable_amount'], Decimal('200.00'))
