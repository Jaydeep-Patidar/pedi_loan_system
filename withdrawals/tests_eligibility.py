from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import Loan, Member, MemberPedi, Payment, Pedi
from withdrawals.eligibility import get_member_withdrawal_eligibility
from withdrawals.models import WithdrawalRequest
from withdrawals.services import can_member_withdraw, create_withdrawal_request


class WithdrawalEligibilityTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='elig', password='pass')
        self.member = Member.objects.create(
            user=user,
            email='e@test.com',
            phone='7777777777',
            role='member',
        )
        self.pedi = Pedi.objects.create(
            name='Elig Pedi',
            duration_months=12,
            monthly_amount=Decimal('200.00'),
            monthly_due_day=10,
            start_date=date(2025, 1, 1),
        )
        MemberPedi.objects.create(
            member=self.member,
            pedi=self.pedi,
            status='Exited',
            membership_start_date=date(2025, 1, 1),
        )
        Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=1,
            year=2025,
            amount=Decimal('200.00'),
            due_date=date(2025, 1, 10),
            status='Paid',
            base_amount_paid=Decimal('200.00'),
            total_paid=Decimal('200.00'),
            payment_date=timezone.now(),
            payment_completed_at=timezone.now(),
        )

    def test_eligible_when_exited_and_paid(self):
        ok, errors = can_member_withdraw(self.member)
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_blocked_with_active_pedi(self):
        MemberPedi.objects.filter(member=self.member).update(status='Active')
        ok, errors = can_member_withdraw(self.member)
        self.assertFalse(ok)
        self.assertTrue(any('pedi' in e.lower() for e in errors))

    def test_blocked_with_active_loan(self):
        Loan.objects.create(
            member=self.member,
            amount=Decimal('1000.00'),
            interest_rate=Decimal('10.00'),
            total_payable=Decimal('1100.00'),
            remaining_due=Decimal('500.00'),
            due_date=date(2026, 1, 1),
            status='Active',
        )
        ok, errors = can_member_withdraw(self.member)
        self.assertFalse(ok)
        self.assertTrue(any('loan' in e.lower() for e in errors))

    def test_blocked_with_pending_pedi_payment(self):
        Payment.objects.create(
            member=self.member,
            pedi=self.pedi,
            month=2,
            year=2025,
            amount=Decimal('200.00'),
            due_date=date(2025, 2, 10),
            status='Pending',
        )
        ok, errors = can_member_withdraw(self.member)
        self.assertFalse(ok)
        self.assertTrue(any('pedi dues' in e.lower() for e in errors))

    def test_blocked_with_exit_requested(self):
        MemberPedi.objects.filter(member=self.member).update(status='Exit Requested')
        elig = get_member_withdrawal_eligibility(self.member)
        self.assertFalse(elig['can_withdraw'])
        self.assertTrue(any('exit request' in e.lower() for e in elig['errors']))

    def test_duplicate_withdrawal_blocked(self):
        WithdrawalRequest.objects.create(
            member=self.member,
            requested_amount=Decimal('200.00'),
            calculated_amount=Decimal('200.00'),
            status='Pending',
        )
        wr, errors = create_withdrawal_request(self.member)
        self.assertIsNone(wr)
        self.assertTrue(any('already submitted' in e.lower() for e in errors))
