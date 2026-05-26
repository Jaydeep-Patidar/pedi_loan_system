from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import Member, MemberPedi, Payment, Loan
from .eligibility import (
    OPEN_WITHDRAWAL_STATUSES,
    get_member_withdrawal_eligibility,
    has_pending_exit_request,
)
from .models import Withdrawal, WithdrawalRequest


def _paid_contributions_queryset(member, since_dt=None):
    """Paid pedi contributions (base only), optionally after last completed withdrawal."""
    qs = Payment.objects.filter(
        member=member,
        status='Paid',
        is_cancelled=False,
    )
    if since_dt:
        qs = qs.filter(
            Q(payment_date__gt=since_dt)
            | Q(payment_date__isnull=True, payment_completed_at__gt=since_dt)
        )
    return qs


def _sum_contributions(payments_qs):
    total = Decimal('0.00')
    for payment in payments_qs.iterator():
        total += payment.get_contribution_collected()
    return total.quantize(Decimal('0.01'))


def _sum_penalties_collected(payments_qs):
    total = Decimal('0.00')
    for payment in payments_qs.iterator():
        total += payment.penalty_paid or Decimal('0.00')
    return total.quantize(Decimal('0.01'))


def _sum_unpaid_penalties(member, today=None):
    today = today or timezone.now().date()
    total = Decimal('0.00')
    pending = Payment.objects.filter(
        member=member,
        status='Pending',
        is_cancelled=False,
    )
    for payment in pending.iterator():
        if payment.is_future_payment(today=today):
            continue
        total += payment.calculate_penalty(today=today)
    return total.quantize(Decimal('0.01'))


def calculate_withdrawal_amount(member, today=None):
    """Calculate final pedi settlement withdrawal for a member."""
    today = today or timezone.now().date()

    last_withdrawal = Withdrawal.objects.filter(
        member=member,
        status='Completed',
    ).order_by('-processed_at').first()

    since_dt = last_withdrawal.processed_at if last_withdrawal else None
    paid_since = _paid_contributions_queryset(member, since_dt=since_dt)

    total_contribution = _sum_contributions(paid_since)
    penalties_collected = _sum_penalties_collected(paid_since)
    unpaid_penalties = _sum_unpaid_penalties(member, today=today)

    withdrawable_amount = (total_contribution - unpaid_penalties).quantize(Decimal('0.01'))
    if withdrawable_amount < 0:
        withdrawable_amount = Decimal('0.00')

    all_time_contribution = _sum_contributions(_paid_contributions_queryset(member))
    all_time_penalties = _sum_penalties_collected(_paid_contributions_queryset(member))

    return {
        'total_contribution_paid': total_contribution,
        'penalties_already_paid': penalties_collected,
        'unpaid_penalties_due': unpaid_penalties,
        'withdrawable_amount': withdrawable_amount,
        'all_time_contribution': all_time_contribution,
        'all_time_penalties_paid': all_time_penalties,
        'since_last_withdrawal': since_dt is not None,
        'total_pedi_paid': total_contribution,
        'total_pedi_penalties': unpaid_penalties,
        'total_penalties': unpaid_penalties,
        'total_paid': total_contribution,
        'total_loan_paid': Decimal('0.00'),
        'total_loan_penalties': Decimal('0.00'),
    }


def get_member_withdrawal_snapshot(member):
    """Admin/member dashboard: eligibility + amounts + status summaries."""
    eligibility = get_member_withdrawal_eligibility(member)
    calc = calculate_withdrawal_amount(member)
    active_loans = Loan.objects.filter(member=member, status='Active').count()
    return {
        'eligibility': eligibility,
        'calculation': calc,
        'can_withdraw': eligibility['can_withdraw'] and calc['withdrawable_amount'] > 0,
        'errors': list(eligibility['errors']),
        'loan_status': eligibility['loan']['loan_status_summary'],
        'pedi_status': eligibility['pedi_memberships']['pedi_status_summary'],
        'active_loan_count': eligibility['loan']['active_loan_count'],
        'pending_pedi_count': eligibility['pedi_payments']['pending_payment_count'],
        'withdrawable_amount': calc['withdrawable_amount'],
        'total_contribution': calc['all_time_contribution'],
        'total_penalties_paid': calc['all_time_penalties_paid'],
    }


def can_member_withdraw(member):
    """Check if member can request withdrawal."""
    eligibility = get_member_withdrawal_eligibility(member)
    errors = list(eligibility['errors'])

    calc = calculate_withdrawal_amount(member)
    if calc['all_time_contribution'] <= 0:
        errors.append('Cannot withdraw: No paid pedi contributions to withdraw.')

    if eligibility['can_withdraw'] and calc['withdrawable_amount'] <= 0:
        errors.append(
            'Cannot withdraw: Your withdrawable amount is zero (unpaid penalties may exceed contributions).'
        )

    return len(errors) == 0, errors


def has_pending_withdrawal(member):
    """Member has a pending withdrawal request awaiting admin action."""
    return WithdrawalRequest.objects.filter(member=member, status='Pending').exists()


def has_open_withdrawal_request(member):
    """Pending or approved (under review) — blocks duplicate requests."""
    return WithdrawalRequest.objects.filter(
        member=member,
        status__in=OPEN_WITHDRAWAL_STATUSES,
    ).exists()


@transaction.atomic
def create_withdrawal_request(member, remarks=''):
    """Create a withdrawal request for member."""
    member = Member.objects.select_for_update().get(pk=member.pk)

    can_withdraw, errors = can_member_withdraw(member)
    if not can_withdraw:
        return None, errors

    if has_open_withdrawal_request(member):
        return None, ['Withdrawal request already submitted.']

    calc = calculate_withdrawal_amount(member)
    if calc['withdrawable_amount'] <= 0:
        return None, ['Cannot create withdrawal request: withdrawable amount is zero.']

    wr = WithdrawalRequest.objects.create(
        member=member,
        requested_amount=calc['withdrawable_amount'],
        calculated_amount=calc['withdrawable_amount'],
        remarks=remarks,
        status='Pending',
    )

    return wr, []


@transaction.atomic
def approve_withdrawal_request(withdrawal_request, approved_by, notes=''):
    """Admin approves withdrawal request and creates withdrawal record."""
    wr = WithdrawalRequest.objects.select_for_update().get(pk=withdrawal_request.pk)

    if wr.status != 'Pending':
        return None, 'Request is not pending.'

    can_withdraw, errors = can_member_withdraw(wr.member)
    if not can_withdraw:
        return None, ' '.join(errors[:3])

    calc = calculate_withdrawal_amount(wr.member)
    if calc['withdrawable_amount'] <= 0:
        return None, 'Cannot approve: withdrawable amount is currently zero.'

    withdrawal = Withdrawal.objects.create(
        member=wr.member,
        withdrawal_request=wr,
        total_paid_amount=calc['total_contribution_paid'],
        total_penalties_paid=calc['unpaid_penalties_due'],
        withdrawal_amount=calc['withdrawable_amount'],
        status='Pending',
        processed_by=approved_by,
        notes=notes,
        reason='Withdrawal approved by admin',
    )

    wr.status = 'Approved'
    wr.calculated_amount = calc['withdrawable_amount']
    wr.save(update_fields=['status', 'calculated_amount', 'updated_at'])

    return withdrawal, None


@transaction.atomic
def process_withdrawal_payment(withdrawal, payment_method='Cash', transaction_reference='', notes=''):
    """Process withdrawal payment, deactivate member, and close pedi memberships."""
    locked = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)

    if locked.status != 'Pending':
        return False, 'Withdrawal is not in pending status.'

    locked.payment_method = payment_method
    locked.transaction_reference = transaction_reference
    if notes:
        locked.notes = notes
    locked.mark_completed()

    if locked.withdrawal_request_id:
        wr = WithdrawalRequest.objects.select_for_update().get(pk=locked.withdrawal_request_id)
        wr.status = 'Withdrawn'
        wr.save(update_fields=['status', 'updated_at'])

    return True, 'Withdrawal processed successfully.'


def reject_withdrawal_request(withdrawal_request, reason=''):
    """Admin rejects withdrawal request."""
    if withdrawal_request.status != 'Pending':
        return False, 'Request is not pending.'

    withdrawal_request.status = 'Rejected'
    withdrawal_request.remarks = reason
    withdrawal_request.save(update_fields=['status', 'remarks', 'updated_at'])

    return True, 'Withdrawal request rejected.'


def get_admin_request_metrics():
    """Counts for admin dashboard."""
    return {
        'pending_exit_count': MemberPedi.objects.filter(status='Exit Requested').count(),
        'pending_withdrawal_count': WithdrawalRequest.objects.filter(status='Pending').count(),
        'under_review_withdrawal_count': WithdrawalRequest.objects.filter(status='Approved').count(),
        'approved_withdrawal_count': WithdrawalRequest.objects.filter(status='Approved').count(),
        'rejected_withdrawal_count': WithdrawalRequest.objects.filter(status='Rejected').count(),
        'withdrawn_count': WithdrawalRequest.objects.filter(status='Withdrawn').count(),
    }
