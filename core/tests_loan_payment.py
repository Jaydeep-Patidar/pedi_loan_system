from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import Loan, LoanPayment, Member
from core.utils_loan_payment import complete_loan_payment, get_loan_payment_breakdown


class LoanPaymentPenaltyTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='loanuser', password='pass')
        self.member = Member.objects.create(
            user=user,
            email='l@test.com',
            phone='6666666666',
            role='member',
        )
        self.loan = Loan.objects.create(
            member=self.member,
            amount=Decimal('10000.00'),
            interest_rate=Decimal('0.00'),
            total_payable=Decimal('1000.00'),
            paid_amount=Decimal('0.00'),
            remaining_due=Decimal('1000.00'),
            due_date=date.today() - timedelta(days=30),
            penalty_enabled=True,
            grace_days=5,
            enable_fixed_penalty=True,
            fixed_penalty_amount=Decimal('50.00'),
            status='Active',
        )

    def test_breakdown_includes_penalty(self):
        breakdown = get_loan_payment_breakdown(self.loan, Decimal('1000.00'))
        self.assertEqual(breakdown['base_amount'], Decimal('1000.00'))
        self.assertEqual(breakdown['penalty_amount'], Decimal('50.00'))
        self.assertEqual(breakdown['final_payable'], Decimal('1050.00'))

    def test_complete_loan_payment_freezes_penalty(self):
        payment, error = complete_loan_payment(
            self.loan,
            Decimal('1000.00'),
            payment_method='Cash',
            transaction_id='TEST-LOAN-1',
        )
        self.assertIsNone(error)
        self.loan.refresh_from_db()
        self.assertEqual(payment.penalty_paid, Decimal('50.00'))
        self.assertEqual(payment.total_paid, Decimal('1050.00'))
        self.assertEqual(self.loan.paid_amount, Decimal('1000.00'))
        self.assertEqual(self.loan.remaining_due, Decimal('0.00'))
        self.assertEqual(self.loan.status, 'Closed')
        self.assertEqual(self.loan.get_outstanding_penalty(), Decimal('0.00'))

    def test_loan_not_closed_with_unpaid_penalty(self):
        Loan.objects.filter(pk=self.loan.pk).update(
            remaining_due=Decimal('0.00'),
            paid_amount=Decimal('1000.00'),
        )
        self.loan.refresh_from_db()
        self.assertGreater(self.loan.get_outstanding_penalty(), Decimal('0.00'))
        self.assertEqual(self.loan.status, 'Active')
