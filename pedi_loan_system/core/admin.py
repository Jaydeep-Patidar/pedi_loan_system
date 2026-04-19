from django.contrib import admin
from .models import Member, Pedi, MemberPedi, Payment, Loan, LoanPayment, Transaction, LoanTransaction

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'role', 'joined_date', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone']

@admin.register(Pedi)
class PediAdmin(admin.ModelAdmin):
    list_display = ['name', 'monthly_amount', 'duration_months', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active']

@admin.register(MemberPedi)
class MemberPediAdmin(admin.ModelAdmin):
    list_display = ['member', 'pedi', 'joined_date', 'status']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['member', 'pedi', 'month', 'year', 'amount', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'pedi']

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['member', 'amount', 'interest_rate', 'total_payable', 'remaining_due', 'status']
    list_filter = ['status']


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_method']

@admin.register(LoanTransaction)
class LoanTransactionAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'razorpay_order_id', 'status', 'created_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['member', 'amount', 'status', 'created_at']