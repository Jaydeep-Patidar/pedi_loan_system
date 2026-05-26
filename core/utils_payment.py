"""Shared payment completion and breakdown helpers for Pedi monthly payments."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone


def get_payment_breakdown(payment, today=None):
    """Return display/collection breakdown for an unpaid or paid payment."""
    today = today or timezone.now().date()
    due_date = payment.get_due_date_exact()
    grace_days = payment.grace_days_used if payment.status == 'Paid' else payment.grace_days

    if payment.status == 'Paid':
        base = payment.base_amount_paid or payment.amount
        penalty = payment.penalty_paid or Decimal('0.00')
        total = payment.total_paid or (base + penalty)
        effective_status = 'Paid'
    else:
        base = payment.amount
        penalty = payment.calculate_penalty(today=today)
        total = (base + penalty).quantize(Decimal('0.01'))
        effective_status = payment.get_effective_overdue_status(today=today)

    return {
        'base_amount': base,
        'penalty_amount': penalty,
        'final_payable': total,
        'due_date': due_date,
        'grace_days': grace_days,
        'effective_status': effective_status,
        'overdue_days': payment.overdue_days() if payment.status != 'Paid' else 0,
    }


@transaction.atomic
def complete_payment(
    payment,
    *,
    payment_method,
    transaction_id=None,
    razorpay_order_id=None,
    razorpay_payment_id=None,
):
    """Mark a payment as paid and freeze penalty/grace/totals at completion time.

    Must be called while payment.status is not yet 'Paid'.
    Returns the payment instance (refreshed).
    """
    locked = payment.__class__.objects.select_for_update().get(pk=payment.pk)

    if locked.status == 'Paid':
        return locked

    today = timezone.now().date()
    penalty = locked.calculate_penalty(today=today)
    base = locked.amount
    total = (base + penalty).quantize(Decimal('0.01'))
    now = timezone.now()

    locked.base_amount_paid = base
    locked.penalty_paid = penalty
    locked.total_paid = total
    locked.grace_days_used = locked.grace_days
    locked.status = 'Paid'
    locked.payment_date = now
    locked.payment_completed_at = now
    locked.payment_method = payment_method

    if transaction_id:
        locked.transaction_id = transaction_id
    if razorpay_order_id:
        locked.razorpay_order_id = razorpay_order_id
    if razorpay_payment_id:
        locked.razorpay_payment_id = razorpay_payment_id

    locked.save()
    return locked
