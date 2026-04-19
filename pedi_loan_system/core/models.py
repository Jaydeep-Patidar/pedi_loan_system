from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Member(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
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

    class Meta:
        unique_together = ('member', 'pedi', 'month', 'year')

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
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Closed', 'Closed')], default='Active')

    def save(self, *args, **kwargs):
        if not self.total_payable:
            self.total_payable = self.amount + (self.amount * self.interest_rate / 100)
        self.remaining_due = self.total_payable - self.paid_amount
        if self.remaining_due <= 0:
            self.status = 'Closed'
        super().save(*args, **kwargs)

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

class LoanPayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Cash', 'Cash')], default='Online')
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.loan.paid_amount += self.amount
        self.loan.save()

class Transaction(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('Created', 'Created'), ('Success', 'Success'), ('Failed', 'Failed')], default='Created')
    created_at = models.DateTimeField(auto_now_add=True)

