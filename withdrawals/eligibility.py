"""Withdrawal and exit-request eligibility checks for members."""
from decimal import Decimal

from django.utils import timezone

from core.models import Loan, LoanApplication, MemberPedi, Payment

# Member can withdraw only when every pedi membership is in a terminal/settled state.
ALLOWED_PEDI_MEMBERSHIP_STATUSES = frozenset({'Completed', 'Exited', 'Defaulted'})
BLOCKING_PEDI_MEMBERSHIP_STATUSES = frozenset({'Active', 'Exit Requested'})

# Open withdrawal pipeline — blocks duplicate requests.
OPEN_WITHDRAWAL_STATUSES = frozenset({'Pending', 'Approved'})


def _visible_pending_payments(member, today=None):
    today = today or timezone.now().date()
    qs = Payment.objects.filter(member=member, status='Pending', is_cancelled=False)
    for payment in qs.iterator():
        if payment.is_future_payment(today=today):
            continue
        yield payment


def check_loan_eligibility(member):
    """All loans must be Closed with no remaining due or overdue penalty."""
    errors = []
    loans = list(Loan.objects.filter(member=member))

    if LoanApplication.objects.filter(member=member, status='Pending').exists():
        errors.append('Complete all pending loans before withdrawal. (Loan application pending approval.)')

    non_closed = [ln for ln in loans if ln.status != 'Closed']
    if non_closed:
        errors.append('Complete all pending loans before withdrawal.')

    for loan in loans:
        remaining = loan.remaining_due or Decimal('0.00')
        if remaining > 0:
            errors.append('Complete all pending loans before withdrawal.')
            break
        if loan.status == 'Active' and loan.calculate_penalty() > 0:
            errors.append('Complete all pending loans before withdrawal. (Unpaid loan penalty.)')
            break

    active_count = sum(1 for ln in loans if ln.status == 'Active')
    return {
        'ok': not errors,
        'errors': errors,
        'active_loan_count': active_count,
        'total_loans': len(loans),
        'loan_status_summary': 'All Closed' if loans and not non_closed else (
            f'{len(non_closed)} not closed' if non_closed else 'No loans'
        ),
    }


def check_pedi_payment_eligibility(member, today=None):
    """All visible current/past pedi payments must be paid; no unpaid penalty."""
    today = today or timezone.now().date()
    errors = []
    pending_count = 0
    overdue_count = 0
    unpaid_penalty = Decimal('0.00')

    for payment in _visible_pending_payments(member, today=today):
        pending_count += 1
        if payment.get_effective_overdue_status(today=today) == 'Overdue':
            overdue_count += 1
        unpaid_penalty += payment.calculate_penalty(today=today)

    if pending_count:
        if overdue_count:
            errors.append('Clear all pedi dues before withdrawal. (Overdue payments outstanding.)')
        else:
            errors.append('Clear all pedi dues before withdrawal.')

    if unpaid_penalty > 0 and not pending_count:
        errors.append('Clear all pedi dues before withdrawal. (Unpaid penalties outstanding.)')

    return {
        'ok': not errors,
        'errors': errors,
        'pending_payment_count': pending_count,
        'overdue_payment_count': overdue_count,
        'unpaid_penalty': unpaid_penalty.quantize(Decimal('0.01')),
    }


def check_pedi_membership_eligibility(member):
    """All pedi memberships must be Completed, Exited, or Defaulted (not Active / Exit Requested)."""
    errors = []
    memberships = list(MemberPedi.objects.filter(member=member).select_related('pedi'))

    if not memberships:
        errors.append('No pedi membership found. Contact admin if you believe this is an error.')
        return {
            'ok': False,
            'errors': errors,
            'memberships': [],
            'pedi_status_summary': 'No memberships',
        }

    blocking = [mp for mp in memberships if mp.status in BLOCKING_PEDI_MEMBERSHIP_STATUSES]
    if blocking:
        active = [mp for mp in blocking if mp.status == 'Active']
        exit_req = [mp for mp in blocking if mp.status == 'Exit Requested']
        if active:
            errors.append(
                'All pedi memberships must be closed before withdrawal. Please exit all active pedis first.'
            )
        if exit_req:
            errors.append('Exit request already pending approval.')

    disallowed = [mp for mp in memberships if mp.status not in ALLOWED_PEDI_MEMBERSHIP_STATUSES]
    if disallowed and not blocking:
        names = ', '.join({mp.status for mp in disallowed})
        errors.append(f'Pedi membership not eligible for withdrawal (status: {names}).')

    summary_parts = []
    for mp in memberships:
        summary_parts.append(f'{mp.pedi.name}: {mp.status}')

    return {
        'ok': not errors,
        'errors': errors,
        'memberships': memberships,
        'pedi_status_summary': '; '.join(summary_parts),
    }


def has_pending_exit_request(member):
    return MemberPedi.objects.filter(member=member, status='Exit Requested').exists()


def get_member_withdrawal_eligibility(member, today=None):
    """Full eligibility snapshot for withdrawal requests."""
    today = today or timezone.now().date()
    from .models import WithdrawalRequest

    loan_check = check_loan_eligibility(member)
    pedi_pay_check = check_pedi_payment_eligibility(member, today=today)
    pedi_member_check = check_pedi_membership_eligibility(member)

    errors = []
    errors.extend(loan_check['errors'])
    errors.extend(pedi_pay_check['errors'])
    errors.extend(pedi_member_check['errors'])

    open_withdrawal = WithdrawalRequest.objects.filter(
        member=member,
        status__in=OPEN_WITHDRAWAL_STATUSES,
    ).first()
    if open_withdrawal:
        if open_withdrawal.status == 'Pending':
            errors.append('Withdrawal request already submitted.')
        else:
            errors.append('Withdrawal request already submitted and is under admin review.')

    return {
        'can_withdraw': len(errors) == 0,
        'errors': errors,
        'loan': loan_check,
        'pedi_payments': pedi_pay_check,
        'pedi_memberships': pedi_member_check,
        'open_withdrawal_request': open_withdrawal,
        'has_pending_exit': has_pending_exit_request(member),
    }


def can_member_request_exit(member, pedi_id=None):
    """Whether member may submit (or update) a pedi exit request."""
    errors = []

    from .models import WithdrawalRequest
    if WithdrawalRequest.objects.filter(member=member, status__in=OPEN_WITHDRAWAL_STATUSES).exists():
        errors.append('Cannot submit exit request while a withdrawal request is pending or under review.')

    if pedi_id:
        try:
            membership = MemberPedi.objects.get(member=member, pedi_id=pedi_id)
        except MemberPedi.DoesNotExist:
            errors.append('Membership not found.')
            return False, errors

        if membership.status != 'Active':
            if membership.status == 'Exit Requested':
                return True, []  # allow update on same pedi
            errors.append('Exit request is only available for active pedi memberships.')
            return False, errors

    if has_pending_exit_request(member):
        if pedi_id:
            membership = MemberPedi.objects.get(member=member, pedi_id=pedi_id)
            if membership.status != 'Exit Requested':
                errors.append('Exit request already pending approval on another pedi.')
        else:
            errors.append('Exit request already pending approval.')

    return len(errors) == 0, errors
