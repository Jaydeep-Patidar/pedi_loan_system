"""Loan payment breakdown and completion helpers."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Loan, LoanPayment


def get_loan_payment_breakdown(loan, base_amount, today=None):
    """Return EMI/base, penalty, and final payable for a loan payment."""
    today = today or timezone.now().date()
    base = Decimal(str(base_amount)).quantize(Decimal('0.01'))
    if base < 0:
        base = Decimal('0.00')

    remaining = loan.remaining_due or Decimal('0.00')
    if base > remaining and remaining > 0:
        base = remaining
    elif remaining <= 0:
        base = Decimal('0.00')

    penalty = loan.get_outstanding_penalty(today=today)
    if base <= 0 and penalty <= 0:
        penalty = Decimal('0.00')

    final_payable = (base + penalty).quantize(Decimal('0.01'))

    return {
        'base_amount': base,
        'penalty_amount': penalty,
        'final_payable': final_payable,
        'due_date': loan.due_date,
        'grace_days': loan.grace_days,
        'remaining_due': remaining,
        'is_overdue': loan.is_overdue(today=today),
        'overdue_days': loan.overdue_days(today=today),
    }


@transaction.atomic
def complete_loan_payment(
    loan,
    base_amount,
    *,
    payment_method,
    transaction_id=None,
    today=None,
):
    """Record a loan payment and freeze penalty; update loan totals."""
    locked_loan = Loan.objects.select_for_update().get(pk=loan.pk)
    if locked_loan.status == 'Closed':
        return None, 'This loan is already closed.'

    breakdown = get_loan_payment_breakdown(locked_loan, base_amount, today=today)
    if breakdown['final_payable'] <= 0:
        return None, 'Payment amount must be greater than zero.'

    now = timezone.now()
    payment = LoanPayment.objects.create(
        loan=locked_loan,
        amount=breakdown['final_payable'],
        base_amount_paid=breakdown['base_amount'],
        penalty_paid=breakdown['penalty_amount'],
        total_paid=breakdown['final_payable'],
        grace_days_used=locked_loan.grace_days,
        payment_method=payment_method,
        transaction_id=transaction_id or '',
        payment_completed_at=now,
    )
    payment.payment_date = now
    payment.save(update_fields=['payment_date'])

    locked_loan.refresh_from_db()
    return payment, None
