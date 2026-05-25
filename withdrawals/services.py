from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum
from core.models import Member, MemberPedi, Payment, Loan, LoanPayment
from .models import Withdrawal, WithdrawalRequest


def can_member_withdraw(member):
    """Check if member can request withdrawal."""
    errors = []

    active_loans = Loan.objects.filter(member=member, status='Active')
    if active_loans.exists():
        errors.append("Cannot withdraw: You have active loans that need to be closed.")
        return False, errors

    active_pedis = MemberPedi.objects.filter(member=member, status='Active')
    if active_pedis.exists():
        errors.append("Cannot withdraw: You have active pedi memberships. Please exit all pedis first.")
        return False, errors

    total_paid = Payment.objects.filter(
        member=member,
        status='Paid',
        is_cancelled=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    if total_paid <= 0:
        errors.append("Cannot withdraw: No paid amounts to withdraw.")
        return False, errors

    calc = calculate_withdrawal_amount(member)
    if calc.get('withdrawable_amount', Decimal('0.00')) <= 0:
        errors.append("Cannot withdraw: Your withdrawable amount is zero.")
        return False, errors

    return True, []


def calculate_withdrawal_amount(member):
    """Calculate withdrawal amount for a member."""
    last_withdrawal = Withdrawal.objects.filter(
        member=member,
        status='Completed'
    ).order_by('-processed_at').first()

    payment_filter = Payment.objects.filter(
        member=member,
        status='Paid',
        is_cancelled=False
    )

    if last_withdrawal:
        payment_filter = payment_filter.filter(payment_date__gt=last_withdrawal.processed_at)

    pedi_payments = payment_filter.aggregate(total_paid=Sum('amount'))
    total_pedi_paid = pedi_payments['total_paid'] or Decimal('0.00')

    pedi_penalties = Decimal('0.00')
    pending_payments = Payment.objects.filter(member=member, status='Pending')
    for payment in pending_payments:
        pedi_penalties += payment.calculate_penalty()

    withdrawable_amount = total_pedi_paid - pedi_penalties
    if withdrawable_amount < 0:
        withdrawable_amount = Decimal('0.00')

    return {
        'total_pedi_paid': total_pedi_paid,
        'total_loan_paid': Decimal('0.00'),
        'total_paid': total_pedi_paid,
        'total_pedi_penalties': pedi_penalties,
        'total_loan_penalties': Decimal('0.00'),
        'total_penalties': pedi_penalties,
        'withdrawable_amount': withdrawable_amount,
    }


def create_withdrawal_request(member, remarks=''):
    """Create a withdrawal request for member."""
    can_withdraw, errors = can_member_withdraw(member)
    if not can_withdraw:
        return None, errors

    calc = calculate_withdrawal_amount(member)
    if calc.get('withdrawable_amount', Decimal('0.00')) <= 0:
        return None, ["Cannot create withdrawal request: withdrawable amount is zero."]

    existing = WithdrawalRequest.objects.filter(
        member=member,
        status__in=['Pending', 'Approved']
    ).exists()

    if existing:
        return None, ["A pending or approved withdrawal request already exists."]

    wr = WithdrawalRequest.objects.create(
        member=member,
        requested_amount=calc['withdrawable_amount'],
        calculated_amount=calc['withdrawable_amount'],
        remarks=remarks,
        status='Pending'
    )

    return wr, []


def approve_withdrawal_request(withdrawal_request, approved_by, notes=''):
    """Admin approves withdrawal request and creates withdrawal record."""
    if withdrawal_request.status != 'Pending':
        return None, "Request is not pending."

    calc = calculate_withdrawal_amount(withdrawal_request.member)

    withdrawal = Withdrawal.objects.create(
        member=withdrawal_request.member,
        withdrawal_request=withdrawal_request,
        total_paid_amount=calc['total_paid'],
        total_penalties_paid=calc['total_penalties'],
        withdrawal_amount=calc['withdrawable_amount'],
        status='Pending',
        processed_by=approved_by,
        notes=notes,
        reason='Withdrawal approved by admin'
    )

    withdrawal_request.status = 'Approved'
    withdrawal_request.save()

    return withdrawal, None


def process_withdrawal_payment(withdrawal, payment_method='Cash', transaction_reference='', notes=''):
    """Process withdrawal payment and deactivate member."""
    if withdrawal.status != 'Pending':
        return False, "Withdrawal is not in pending status."

    withdrawal.payment_method = payment_method
    withdrawal.transaction_reference = transaction_reference
    withdrawal.notes = notes
    withdrawal.mark_completed()

    if withdrawal.withdrawal_request:
        withdrawal.withdrawal_request.status = 'Withdrawn'
        withdrawal.withdrawal_request.save()

    return True, "Withdrawal processed successfully."


def reject_withdrawal_request(withdrawal_request, reason=''):
    """Admin rejects withdrawal request."""
    if withdrawal_request.status != 'Pending':
        return False, "Request is not pending."

    withdrawal_request.status = 'Rejected'
    withdrawal_request.remarks = reason
    withdrawal_request.save()

    return True, "Withdrawal request rejected."


def has_pending_withdrawal(member):
    """Check if member has a pending withdrawal request."""
    return WithdrawalRequest.objects.filter(member=member, status='Pending').exists()
