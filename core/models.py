from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from .utils_penalties import _ensure_single_penalty_method

class Member(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def total_paid(self):
        """Total amount collected from this member (base + penalty), with legacy fallback."""
        paid = self.payments.filter(status='Paid', is_cancelled=False)
        total = Decimal('0.00')
        for p in paid.only('amount', 'base_amount_paid', 'penalty_paid', 'total_paid'):
            total += p.get_collected_total()
        return total

    @property
    def total_contribution_paid(self):
        paid = self.payments.filter(status='Paid', is_cancelled=False)
        total = Decimal('0.00')
        for p in paid.only('amount', 'base_amount_paid'):
            total += p.get_contribution_collected()
        return total

    @property
    def active_loans(self):
        return self.loans.filter(status='Active')

class Pedi(models.Model):
    name = models.CharField(max_length=100)
    duration_months = models.PositiveIntegerField()
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Every month's payment is due on this day-of-month.
    # Validation: 1..28 (keeps due_date always valid for all months).
    monthly_due_day = models.PositiveIntegerField(
        default=1,
    )


    start_date = models.DateField()

    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    PEDI_STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Closed', 'Closed'),
    )
    pedi_status = models.CharField(max_length=20, choices=PEDI_STATUS_CHOICES, default='Active')
    penalty_enabled = models.BooleanField(default=False)
    grace_days = models.PositiveIntegerField(default=0)
    enable_late_fee_per_day = models.BooleanField(default=False)
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_fixed_penalty = models.BooleanField(default=False)
    fixed_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_percentage_penalty = models.BooleanField(default=False)
    percentage_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)


    def save(self, *args, **kwargs):
        # Prevent changing financial fields if memberships or payments already exist
        if self.pk:
            try:
                from .models import MemberPedi, Payment
            except Exception:
                MemberPedi = None
                Payment = None
            try:
                orig = Pedi.objects.get(pk=self.pk)
            except Pedi.DoesNotExist:
                orig = None

            if orig:
                has_members = False
                has_payments = False
                if MemberPedi:
                    has_members = MemberPedi.objects.filter(pedi=orig).exists()
                if Payment:
                    has_payments = Payment.objects.filter(pedi=orig).exists()

                if has_members or has_payments:
                    locked_fields = [
                        'monthly_amount', 'duration_months', 'start_date',
                        'penalty_enabled', 'grace_days', 'enable_late_fee_per_day', 'late_fee_per_day',
                        'enable_fixed_penalty', 'fixed_penalty_amount', 'enable_percentage_penalty', 'percentage_penalty_rate'
                    ]
                    for f in locked_fields:
                        if getattr(self, f) != getattr(orig, f):
                            raise ValidationError("Financial settings cannot be modified after members or payments are created for this pedi.")

        if not self.end_date:
            from dateutil.relativedelta import relativedelta
            self.end_date = self.start_date + relativedelta(months=self.duration_months)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - ₹{self.monthly_amount}/month"

class MemberPedi(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='pedi_memberships')
    pedi = models.ForeignKey(Pedi, on_delete=models.CASCADE, related_name='member_pedis')
    joined_date = models.DateField(auto_now_add=True)
    membership_start_date = models.DateField(default=timezone.now)
    membership_end_date = models.DateField(null=True, blank=True)
    joined_month = models.PositiveIntegerField(null=True, blank=True)
    exit_date = models.DateField(null=True, blank=True)
    exit_reason = models.TextField(blank=True)
    closed_date = models.DateField(blank=True, null=True)
    closed_reason = models.TextField(blank=True)
    member_exit_requested_at = models.DateTimeField(null=True, blank=True)
    member_exit_request_reason = models.TextField(blank=True)
    admin_exit_at = models.DateTimeField(null=True, blank=True)
    admin_exit_reason = models.TextField(blank=True)

    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Exit Requested', 'Exit Requested'),
        ('Completed', 'Completed'),
        ('Defaulted', 'Defaulted'),
        ('Exited', 'Exited'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    class Meta:
        unique_together = ('member', 'pedi')

    def save(self, *args, **kwargs):
        if self.membership_start_date and not self.joined_month:
            self.joined_month = self.membership_start_date.month
        super().save(*args, **kwargs)

    @property
    def is_active_membership(self):
        today = timezone.now().date()
        if self.membership_end_date and self.membership_end_date < today:
            return False
        return self.status == 'Active'

    def __str__(self):
        return f"{self.member.user.username} - {self.pedi.name}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    pedi = models.ForeignKey(Pedi, on_delete=models.CASCADE, related_name='payments')
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Backward compatible: old rows may have Pending/Paid only.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # Exact due date (day-level). For legacy rows, can be null until backfilled.
    due_date = models.DateField(null=True, blank=True)

    payment_date = models.DateTimeField(null=True, blank=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    grace_days_used = models.PositiveIntegerField(default=0)
    payment_method = models.CharField(max_length=50, choices=[('Cash', 'Cash'), ('Online', 'Online')], default='Cash')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

    # Frozen values at the time of payment (for accounting/reporting/backward compatibility)
    base_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Penalty configuration is stored per-payment for backward compatibility.

    penalty_enabled = models.BooleanField(default=False)

    grace_days = models.PositiveIntegerField(default=0)
    enable_late_fee_per_day = models.BooleanField(default=False)
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_fixed_penalty = models.BooleanField(default=False)
    fixed_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_percentage_penalty = models.BooleanField(default=False)
    percentage_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        unique_together = ('member', 'pedi', 'month', 'year')

    def get_due_date_exact(self):
        """Return the exact due_date for this payment.

        - If due_date is stored, return it.
        - Otherwise compute using the owning Pedi.monthly_due_day.

        Computation:
          due_date = <payment month/year> @ pedi.monthly_due_day
        """
        if self.due_date:
            return self.due_date

        # Legacy fallback: assume missing due_date means legacy payload.
        monthly_due_day = getattr(self.pedi, 'monthly_due_day', None) or 1
        from datetime import datetime
        return datetime(self.year, self.month, monthly_due_day).date()


    # Backward compatibility for templates/admins that call get_due_date()
    def get_due_date(self):
        return self.get_due_date_exact()

    def is_future_payment(self, today=None):
        today = today or timezone.now().date()
        return (self.year, self.month) > (today.year, today.month)


    def get_effective_overdue_status(self, today=None):
        """Compute Overdue/Pending state for unpaid payments.

        Overdue condition:
          today > due_date + grace_days

        Also: never mark future payments overdue.
        """
        if self.status == 'Paid':
            return 'Paid'

        if not self.penalty_enabled:
            return 'Pending'

        today = today or timezone.now().date()
        if self.is_future_payment(today=today):
            return 'Pending'

        due_date = self.get_due_date_exact()
        threshold = due_date + timedelta(days=self.grace_days)
        if today > threshold:
            return 'Overdue'
        return 'Pending'

    def get_display_grace_days(self):
        if self.status == 'Paid' and self.grace_days_used:
            return self.grace_days_used
        return self.grace_days

    def get_contribution_collected(self):
        if self.status != 'Paid':
            return Decimal('0.00')
        return self.base_amount_paid or self.amount

    def get_collected_total(self):
        if self.status != 'Paid':
            return Decimal('0.00')
        if self.total_paid and self.total_paid > 0:
            return self.total_paid
        return (self.get_contribution_collected() + (self.penalty_paid or Decimal('0.00'))).quantize(Decimal('0.01'))

    def get_final_payable_amount(self, today=None):
        if self.status == 'Paid':
            return self.get_collected_total()
        penalty = self.calculate_penalty(today=today)
        return (self.amount + penalty).quantize(Decimal('0.01'))

    def overdue_days(self, today=None):
        """Return overdue days only for current/past unpaid payments."""
        today = today or timezone.now().date()
        effective_status = self.get_effective_overdue_status(today=today)
        if effective_status != 'Overdue':
            return 0
        due_date = self.get_due_date_exact()
        threshold = due_date + timedelta(days=self.grace_days)
        return (today - threshold).days

    def calculate_penalty(self, today=None):
        """Calculate penalty based on overdue days and penalty settings."""
        if self.status == 'Paid':
            return self.penalty_paid or Decimal('0.00')

        today = today or timezone.now().date()
        effective_status = self.get_effective_overdue_status(today=today)
        if effective_status != 'Overdue' or not self.penalty_enabled:
            return Decimal('0.00')

        days = self.overdue_days(today=today)
        if days <= 0:
            return Decimal('0.00')

        penalty = Decimal('0.00')
        if self.enable_late_fee_per_day:
            penalty += Decimal(days) * self.late_fee_per_day
        if self.enable_fixed_penalty:
            penalty += self.fixed_penalty_amount
        if self.enable_percentage_penalty:
            penalty += (self.amount * self.percentage_penalty_rate / Decimal('100'))
        return penalty.quantize(Decimal('0.01'))

    @classmethod
    def aggregate_paid_totals(cls, queryset=None):
        """Return contribution, fine, and total collected for paid payments."""
        qs = queryset if queryset is not None else cls.objects.filter(status='Paid', is_cancelled=False)
        contribution = Decimal('0.00')
        fine = Decimal('0.00')
        total = Decimal('0.00')
        for p in qs.only('amount', 'base_amount_paid', 'penalty_paid', 'total_paid'):
            contribution += p.get_contribution_collected()
            fine += p.penalty_paid or Decimal('0.00')
            total += p.get_collected_total()
        return {
            'contribution': contribution,
            'fine': fine,
            'total': total,
        }

    def __str__(self):
        return f"{self.member.user.username} - {self.pedi.name} - {self.month}/{self.year}"


class Loan(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loans')
    overdue_days = models.PositiveIntegerField(default=0)
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalty_status = models.CharField(max_length=20, choices=[('None', 'None'), ('Overdue', 'Overdue')], default='None')

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_due = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    issued_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    penalty_enabled = models.BooleanField(default=False)
    grace_days = models.PositiveIntegerField(default=0)
    enable_late_fee_per_day = models.BooleanField(default=False)
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_fixed_penalty = models.BooleanField(default=False)
    fixed_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_percentage_penalty = models.BooleanField(default=False)
    percentage_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Closed', 'Closed')], default='Active')

    def save(self, *args, **kwargs):
        # Prevent changing financial fields if loan payments already exist
        if self.pk:
            try:
                from .models import LoanPayment
            except Exception:
                LoanPayment = None
            if LoanPayment and LoanPayment.objects.filter(loan_id=self.pk).exists():
                try:
                    orig = Loan.objects.get(pk=self.pk)
                except Loan.DoesNotExist:
                    orig = None
                if orig:
                    for f in ('amount', 'interest_rate', 'total_payable'):
                        if getattr(self, f) != getattr(orig, f):
                            raise ValidationError("Loan financial details cannot be changed after payments are recorded.")

        if not self.total_payable:
            self.total_payable = self.amount + (self.amount * self.interest_rate / 100)
        self.remaining_due = (self.total_payable - self.paid_amount).quantize(Decimal('0.01'))
        if self.remaining_due < 0:
            self.remaining_due = Decimal('0.00')
        if self.pk and self.remaining_due <= 0 and self.get_outstanding_penalty() <= 0:
            self.status = 'Closed'
        super().save(*args, **kwargs)
        if self.status == 'Closed':
            try:
                application = self.application
            except LoanApplication.DoesNotExist:
                application = None
            if application and application.status == 'Approved':
                application.status = 'Closed'
                application.save()

    def is_overdue(self, today=None):
        if not self.penalty_enabled or self.status == 'Closed':
            return False
        today = today or timezone.now().date()
        threshold = self.due_date + timedelta(days=self.grace_days)
        return today > threshold

    def overdue_days(self, today=None):
        if not self.penalty_enabled:
            return 0
        today = today or timezone.now().date()
        threshold = self.due_date + timedelta(days=self.grace_days)
        if today <= threshold:
            return 0
        return (today - threshold).days

    def _accrued_penalty(self, today=None):
        """Penalty accrued from overdue rules (before subtracting amounts already paid)."""
        if not self.penalty_enabled or self.status == 'Closed':
            return Decimal('0.00')
        days = self.overdue_days(today=today)
        if days <= 0:
            return Decimal('0.00')
        penalty = Decimal('0.00')
        if self.enable_late_fee_per_day:
            penalty += Decimal(days) * self.late_fee_per_day
        if self.enable_fixed_penalty:
            penalty += self.fixed_penalty_amount
        if self.enable_percentage_penalty:
            penalty += (self.amount * self.percentage_penalty_rate / Decimal('100'))
        return penalty.quantize(Decimal('0.01'))

    def total_penalty_paid(self):
        total = Decimal('0.00')
        for p in self.payments.only('penalty_paid', 'amount'):
            total += p.get_penalty_collected()
        return total.quantize(Decimal('0.01'))

    def get_outstanding_penalty(self, today=None):
        """Penalty still owed (accrued minus penalties already paid on this loan)."""
        accrued = self._accrued_penalty(today=today)
        if accrued <= 0:
            return Decimal('0.00')
        outstanding = (accrued - self.total_penalty_paid()).quantize(Decimal('0.01'))
        return max(outstanding, Decimal('0.00'))

    def calculate_penalty(self, today=None):
        """Backward-compatible alias for outstanding penalty."""
        return self.get_outstanding_penalty(today=today)

    def get_final_payable_for_amount(self, base_amount, today=None):
        base = Decimal(str(base_amount)).quantize(Decimal('0.01'))
        penalty = self.get_outstanding_penalty(today=today)
        remaining = self.remaining_due or Decimal('0.00')
        if base > remaining and remaining > 0:
            base = remaining
        elif remaining <= 0:
            base = Decimal('0.00')
        return (base + penalty).quantize(Decimal('0.01'))

    def refresh_payment_totals(self):
        """Recalculate paid_amount, remaining_due, and closure from payment rows."""
        base_paid = Decimal('0.00')
        for p in self.payments.all():
            base_paid += p.get_base_collected()
        self.paid_amount = base_paid.quantize(Decimal('0.01'))
        self.remaining_due = (self.total_payable - self.paid_amount).quantize(Decimal('0.01'))
        if self.remaining_due < 0:
            self.remaining_due = Decimal('0.00')
        self.penalty_amount = self.total_penalty_paid()
        if self.remaining_due <= 0 and self.get_outstanding_penalty() <= 0:
            self.status = 'Closed'
        elif self.status == 'Closed' and (self.remaining_due > 0 or self.get_outstanding_penalty() > 0):
            self.status = 'Active'
        self.penalty_status = 'Overdue' if self.is_overdue() and self.get_outstanding_penalty() > 0 else 'None'
        return self

    def __str__(self):
        return f"Loan to {self.member.user.username} - ₹{self.amount}"

class LoanPayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    base_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grace_days_used = models.PositiveIntegerField(default=0)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Cash', 'Cash')], default='Online')

    def get_base_collected(self):
        if self.base_amount_paid and self.base_amount_paid > 0:
            return self.base_amount_paid
        if self.penalty_paid and self.total_paid and self.total_paid > self.amount:
            return (self.amount - self.penalty_paid).quantize(Decimal('0.01'))
        return self.amount

    def get_penalty_collected(self):
        if self.penalty_paid:
            return self.penalty_paid
        return Decimal('0.00')

    def get_total_collected(self):
        if self.total_paid and self.total_paid > 0:
            return self.total_paid
        return self.amount

    def save(self, *args, **kwargs):
        if not self.total_paid or self.total_paid <= 0:
            self.total_paid = (self.get_base_collected() + self.get_penalty_collected()).quantize(Decimal('0.01'))
        if not self.amount or self.amount <= 0:
            self.amount = self.total_paid
        super().save(*args, **kwargs)
        loan = Loan.objects.select_for_update().get(pk=self.loan_id)
        loan.refresh_payment_totals()
        loan.save()

    def __str__(self):
        return f"Payment of {self.get_total_collected()} for loan {self.loan.id}"

class LoanTransaction(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('Created', 'Created'), ('Success', 'Success'), ('Failed', 'Failed')], default='Created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.razorpay_order_id} - {self.status}"

class Transaction(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('Created', 'Created'), ('Success', 'Success'), ('Failed', 'Failed')], default='Created')
    created_at = models.DateTimeField(auto_now_add=True)


class LoanApplicationSettings(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    default_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    default_loan_duration_months = models.PositiveIntegerField(default=12)
    penalty_enabled = models.BooleanField(default=False)
    grace_days = models.PositiveIntegerField(default=0)
    enable_late_fee_per_day = models.BooleanField(default=False)
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_fixed_penalty = models.BooleanField(default=False)
    fixed_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_percentage_penalty = models.BooleanField(default=False)
    percentage_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Loan Application Settings"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.is_active:
            LoanApplicationSettings.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        status = 'Active' if self.is_active else 'Inactive'
        created = self.created_at.strftime('%Y-%m-%d') if self.created_at else 'Unknown'
        return f"{status} settings created on {created}"

class LoanApplication(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Closed', 'Closed'),
        ('Rejected', 'Rejected'),
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loan_applications')
    loan = models.OneToOneField('Loan', on_delete=models.SET_NULL, null=True, blank=True, related_name='application')
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    applied_date = models.DateTimeField(auto_now_add=True)
    admin_remarks = models.TextField(blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    approved_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    approved_due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.member.user.username} - ₹{self.requested_amount} - {self.status}"

class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


