from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Member, MemberPedi, Payment


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Withdrawn', 'Withdrawn'),
    )

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='withdrawal_requests')
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_withdrawalrequest'

    def __str__(self):
        return f"Withdrawal Request - {self.member.user.get_full_name()} - ₹{self.requested_amount} ({self.status})"


class Withdrawal(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
    )

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='withdrawals')
    withdrawal_request = models.OneToOneField(WithdrawalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='withdrawal')
    total_paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_penalties_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    withdrawal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    transaction_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='withdrawals_processed')
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    reason = models.TextField(blank=True, help_text="Admin reason for withdrawal")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_withdrawal'

    @transaction.atomic
    def mark_completed(self):
        self.status = 'Completed'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'payment_method', 'transaction_reference', 'notes'])

        member = Member.objects.select_for_update().get(pk=self.member_id)
        member.is_active = False
        member.save(update_fields=['is_active'])

        member.user.is_active = False
        member.user.save(update_fields=['is_active'])

        today = timezone.now().date()
        exit_date = today
        exit_ts = timezone.now()

        for mp in MemberPedi.objects.select_for_update().filter(member=member).exclude(
            status__in=('Exited', 'Completed', 'Defaulted')
        ):
            mp.status = 'Exited'
            mp.exit_date = exit_date
            if not mp.exit_reason:
                mp.exit_reason = 'Final settlement withdrawal'
            mp.admin_exit_at = exit_ts
            mp.admin_exit_reason = 'Final settlement withdrawal'
            mp.save()

        future_payments = Payment.objects.filter(
            member=member,
            status='Pending',
            is_cancelled=False,
        )
        for payment in future_payments:
            if payment.is_future_payment(today=today):
                payment.is_cancelled = True
                payment.save(update_fields=['is_cancelled'])

    def __str__(self):
        return f"Withdrawal - {self.member.user.get_full_name()} - ₹{self.withdrawal_amount} ({self.status})"
