from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

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
        return self.payments.filter(status='Paid').aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def active_loans(self):
        return self.loans.filter(status='Active')

class Pedi(models.Model):
    name = models.CharField(max_length=100)
    duration_months = models.PositiveIntegerField()
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    penalty_enabled = models.BooleanField(default=False)
    grace_days = models.PositiveIntegerField(default=0)
    enable_late_fee_per_day = models.BooleanField(default=False)
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_fixed_penalty = models.BooleanField(default=False)
    fixed_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_percentage_penalty = models.BooleanField(default=False)
    percentage_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
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
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Completed', 'Completed'), ('Defaulted', 'Defaulted')], default='Active')

    class Meta:
        unique_together = ('member', 'pedi')

    def __str__(self):
        return f"{self.member.user.username} - {self.pedi.name}"

class Payment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    pedi = models.ForeignKey(Pedi, on_delete=models.CASCADE, related_name='payments')
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('Paid', 'Paid'), ('Pending', 'Pending')], default='Pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=[('Cash', 'Cash'), ('Online', 'Online')], default='Cash')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    penalty_enabled = models.BooleanField(default=False)
    grace_days = models.PositiveIntegerField(default=0)
    enable_late_fee_per_day = models.BooleanField(default=False)
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_fixed_penalty = models.BooleanField(default=False)
    fixed_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enable_percentage_penalty = models.BooleanField(default=False)
    percentage_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('member', 'pedi', 'month', 'year')

    def get_due_date(self):
        """Calculate the payment due date based on month and year."""
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        return datetime(self.year, self.month, 1).date() + relativedelta(months=1) - timedelta(days=1)

    def overdue_days(self):
        """Return the number of days overdue if payment is pending and past due."""
        if self.status == 'Paid' or not self.penalty_enabled:
            return 0
        today = timezone.now().date()
        due_date = self.get_due_date()
        threshold = due_date + timedelta(days=self.grace_days)
        if today <= threshold:
            return 0
        return (today - threshold).days

    def calculate_penalty(self):
        """Calculate penalty based on overdue days and penalty settings."""
        if self.status == 'Paid' or not self.penalty_enabled:
            return Decimal('0.00')
        days = self.overdue_days()
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

    def __str__(self):
        return f"{self.member.user.username} - {self.pedi.name} - {self.month}/{self.year}"

class Loan(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loans')
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
        if not self.total_payable:
            self.total_payable = self.amount + (self.amount * self.interest_rate / 100)
        self.remaining_due = self.total_payable - self.paid_amount
        if self.remaining_due <= 0:
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

    def overdue_days(self):
        if not self.penalty_enabled:
            return 0
        today = timezone.now().date()
        threshold = self.due_date + timedelta(days=self.grace_days)
        if today <= threshold:
            return 0
        return (today - threshold).days

    def calculate_penalty(self):
        if not self.penalty_enabled:
            return Decimal('0.00')
        days = self.overdue_days()
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

    def __str__(self):
        return f"Loan to {self.member.user.username} - ₹{self.amount}"

class LoanPayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Cash', 'Cash')], default='Online')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update loan totals
        total_paid = self.loan.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        self.loan.paid_amount = total_paid
        self.loan.remaining_due = self.loan.total_payable - total_paid
        if self.loan.remaining_due <= 0:
            self.loan.status = 'Closed'
        self.loan.save()

    def __str__(self):
        return f"Payment of {self.amount} for loan {self.loan.id}"

class LoanTransaction(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
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

    class Meta:
        verbose_name_plural = "Loan Application Settings"

    def __str__(self):
        return f"Applications open from {self.start_date} to {self.end_date}"

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