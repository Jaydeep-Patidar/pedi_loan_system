from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError

from core.models import Member, MemberPedi, Payment, Loan, LoanPayment


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

    def mark_completed(self):
        self.status = 'Completed'
        self.processed_at = timezone.now()
        self.save()

        self.member.is_active = False
        self.member.save()

        active_pedis = MemberPedi.objects.filter(member=self.member, status='Active')
        for mp in active_pedis:
            mp.status = 'Exited'
            mp.exit_date = timezone.now().date()
            mp.exit_reason = 'Member withdrew - final settlement'
            mp.admin_exit_at = timezone.now()
            mp.admin_exit_reason = 'Final settlement withdrawal'
            mp.save()

    def __str__(self):
        return f"Withdrawal - {self.member.user.get_full_name()} - ₹{self.withdrawal_amount} ({self.status})"
