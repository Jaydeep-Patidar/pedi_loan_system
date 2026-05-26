from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from core.decorators import admin_required, member_required
from core.models import Member
from core.utils import paginate_queryset
from .models import Withdrawal, WithdrawalRequest
from .forms import WithdrawalRequestForm, WithdrawalApprovalForm
from .services import (
    approve_withdrawal_request,
    calculate_withdrawal_amount,
    can_member_withdraw,
    create_withdrawal_request,
    get_member_withdrawal_snapshot,
    has_open_withdrawal_request,
    has_pending_withdrawal,
    process_withdrawal_payment as complete_withdrawal_payment,
    reject_withdrawal_request,
)


@login_required
@member_required
def request_withdrawal(request):
    member = request.user.member_profile
    snapshot = get_member_withdrawal_snapshot(member)
    can_withdraw = snapshot['can_withdraw']
    errors = snapshot['errors']
    calc = snapshot['calculation']
    has_open = has_open_withdrawal_request(member)

    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST)
        if has_open:
            messages.error(request, 'Withdrawal request already submitted.')
        elif form.is_valid():
            remarks = form.cleaned_data.get('remarks', '')
            wr, errors = create_withdrawal_request(member, remarks=remarks)

            if wr:
                messages.success(request, 'Withdrawal request submitted successfully. Awaiting admin approval.')
                return redirect('withdrawal_requests_list')
            else:
                for error in errors:
                    messages.error(request, error)
        else:
            messages.error(request, 'Form validation failed.')
    else:
        form = WithdrawalRequestForm()

    context = {
        'form': form,
        'can_withdraw': can_withdraw,
        'errors': errors,
        'calculation': calc,
        'has_pending_withdrawal': has_open,
        'eligibility': snapshot['eligibility'],
        'snapshot': snapshot,
    }
    return render(request, 'withdrawals/withdrawal_request_form.html', context)


@login_required
@member_required
def withdrawal_requests_list(request):
    member = request.user.member_profile
    requests = WithdrawalRequest.objects.filter(member=member).order_by('-created_at')
    page_obj = paginate_queryset(request, requests, default_per_page=10)

    context = {
        'requests': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'withdrawals/withdrawal_requests_list.html', context)


@login_required
@member_required
def withdrawal_detail(request, pk):
    member = request.user.member_profile
    wr = get_object_or_404(WithdrawalRequest, pk=pk, member=member)
    withdrawal = Withdrawal.objects.filter(withdrawal_request=wr).first()

    context = {
        'request_obj': wr,
        'withdrawal': withdrawal,
    }
    return render(request, 'withdrawals/withdrawal_detail.html', context)


@login_required
@admin_required
def withdrawal_requests_admin_list(request):
    requests = WithdrawalRequest.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = requests.filter(status=status_filter)

    search_term = request.GET.get('search', '')
    if search_term:
        requests = requests.filter(
            Q(member__user__first_name__icontains=search_term) |
            Q(member__user__last_name__icontains=search_term) |
            Q(member__user__username__icontains=search_term)
        )

    page_obj = paginate_queryset(request, requests, default_per_page=15)

    enriched = []
    for wr in page_obj:
        snap = get_member_withdrawal_snapshot(wr.member)
        enriched.append({'request': wr, 'snapshot': snap})

    context = {
        'requests': page_obj,
        'enriched_requests': enriched,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_term': search_term,
        'status_counts': {
            'Pending': WithdrawalRequest.objects.filter(status='Pending').count(),
            'Approved': WithdrawalRequest.objects.filter(status='Approved').count(),
            'Rejected': WithdrawalRequest.objects.filter(status='Rejected').count(),
            'Withdrawn': WithdrawalRequest.objects.filter(status='Withdrawn').count(),
        },
    }
    return render(request, 'withdrawals/withdrawal_admin_list.html', context)


@login_required
@admin_required
def withdrawal_admin_detail(request, pk):
    wr = get_object_or_404(WithdrawalRequest, pk=pk)
    snapshot = get_member_withdrawal_snapshot(wr.member)
    withdrawal = Withdrawal.objects.filter(withdrawal_request=wr).first()

    context = {
        'request_obj': wr,
        'calculation': snapshot['calculation'],
        'snapshot': snapshot,
        'withdrawal': withdrawal,
    }
    return render(request, 'withdrawals/withdrawal_admin_detail.html', context)


@login_required
@admin_required
def approve_withdrawal(request, pk):
    wr = get_object_or_404(WithdrawalRequest, pk=pk)
    if wr.status != 'Pending':
        messages.error(request, 'This request is not pending.')
        return redirect('withdrawal_requests_admin_list')

    if request.method == 'POST':
        form = WithdrawalApprovalForm(request.POST)
        if form.is_valid():
            notes = form.cleaned_data.get('notes', '')
            withdrawal, error = approve_withdrawal_request(wr, approved_by=request.user, notes=notes)
            if error:
                messages.error(request, error)
            else:
                messages.success(request, 'Withdrawal request approved. Withdrawal record created.')
                return redirect('withdrawal_admin_detail', pk=wr.pk)
    else:
        form = WithdrawalApprovalForm()

    snap = get_member_withdrawal_snapshot(wr.member)
    context = {
        'request_obj': wr,
        'form': form,
        'calculation': snap['calculation'],
        'snapshot': snap,
    }
    return render(request, 'withdrawals/withdrawal_approve_form.html', context)


@login_required
@admin_required
def reject_withdrawal(request, pk):
    wr = get_object_or_404(WithdrawalRequest, pk=pk)
    if wr.status != 'Pending':
        messages.error(request, 'This request is not pending.')
        return redirect('withdrawal_requests_admin_list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        success, msg = reject_withdrawal_request(wr, reason=reason)
        if success:
            messages.success(request, msg)
            return redirect('withdrawal_requests_admin_list')
        else:
            messages.error(request, msg)

    context = {
        'request_obj': wr,
    }
    return render(request, 'withdrawals/withdrawal_reject_form.html', context)


@login_required
@admin_required
def process_withdrawal_payment(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    if withdrawal.status != 'Pending':
        messages.error(request, 'This withdrawal is not pending.')
        return redirect('withdrawal_admin_list')

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'Cash')
        transaction_reference = request.POST.get('transaction_reference', '')
        notes = request.POST.get('notes', '')
        success, msg = complete_withdrawal_payment(
            withdrawal,
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            notes=notes,
        )
        if success:
            messages.success(request, msg)
            return redirect('withdrawal_receipt', pk=withdrawal.pk)
        else:
            messages.error(request, msg)

    context = {
        'withdrawal': withdrawal,
    }
    return render(request, 'withdrawals/withdrawal_process_payment.html', context)


@login_required
@admin_required
def withdrawal_admin_list(request):
    withdrawals = Withdrawal.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        withdrawals = withdrawals.filter(status=status_filter)

    search_term = request.GET.get('search', '')
    if search_term:
        withdrawals = withdrawals.filter(
            Q(member__user__first_name__icontains=search_term) |
            Q(member__user__last_name__icontains=search_term) |
            Q(member__user__username__icontains=search_term)
        )

    page_obj = paginate_queryset(request, withdrawals, default_per_page=15)

    context = {
        'withdrawals': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_term': search_term,
    }
    return render(request, 'withdrawals/withdrawal_transactions_list.html', context)


@login_required
def withdrawal_receipt(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    allowed = withdrawal.processed_by_id == request.user.id
    if not allowed and hasattr(request.user, 'member_profile'):
        profile = request.user.member_profile
        allowed = profile.role == 'admin' or profile.id == withdrawal.member_id
    if not allowed:
        messages.error(request, 'You do not have permission to view this receipt.')
        return redirect('dashboard')

    context = {
        'withdrawal': withdrawal,
    }
    return render(request, 'withdrawals/withdrawal_receipt.html', context)

