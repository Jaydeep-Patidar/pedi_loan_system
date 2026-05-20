from django.contrib import admin
from .models import Member, Pedi, MemberPedi, Payment, Loan, LoanPayment, Transaction, LoanTransaction, LoanApplicationSettings, LoanApplication, Notice

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'role', 'joined_date', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone']

@admin.register(Pedi)
class PediAdmin(admin.ModelAdmin):
    list_display = ['name', 'monthly_amount', 'duration_months', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'duration_months', 'monthly_amount', 'start_date', 'end_date', 'is_active')}),
        ('Penalty Settings', {'fields': (
            'penalty_enabled', 'grace_days',
            'enable_late_fee_per_day', 'late_fee_per_day',
            'enable_fixed_penalty', 'fixed_penalty_amount',
            'enable_percentage_penalty', 'percentage_penalty_rate'
        ), 'classes': ('collapse',)}),
    )

@admin.register(MemberPedi)
class MemberPediAdmin(admin.ModelAdmin):
    list_display = ['member', 'pedi', 'joined_date', 'membership_start_date', 'membership_end_date', 'joined_month', 'status']
    list_filter = ['status']
    fields = ['member', 'pedi', 'joined_date', 'membership_start_date', 'joined_month', 'membership_end_date', 'status']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['member', 'pedi', 'month', 'year', 'amount', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'pedi']
    fieldsets = (
        ('Payment Info', {'fields': ('member', 'pedi', 'month', 'year', 'amount', 'status', 'payment_date', 'payment_method')}),
        ('Transaction Details', {'fields': ('transaction_id', 'razorpay_order_id', 'razorpay_payment_id')}),
        ('Penalty Settings', {'fields': (
            'penalty_enabled', 'grace_days',
            'enable_late_fee_per_day', 'late_fee_per_day',
            'enable_fixed_penalty', 'fixed_penalty_amount',
            'enable_percentage_penalty', 'percentage_penalty_rate'
        ), 'classes': ('collapse',)}),
    )

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
 

@admin.register(LoanApplicationSettings)
class LoanApplicationSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'is_active', 'start_date', 'end_date', 'default_interest_rate',
        'default_loan_duration_months', 'grace_days', 'penalty_enabled'
    ]
    list_filter = ['is_active', 'penalty_enabled', 'created_at']
    readonly_fields = ['created_at']
    fields = [
        'is_active', 'created_at', 'start_date', 'end_date', 'default_interest_rate', 'default_loan_duration_months',
        'penalty_enabled', 'grace_days',
        'enable_late_fee_per_day', 'late_fee_per_day',
        'enable_fixed_penalty', 'fixed_penalty_amount',
        'enable_percentage_penalty', 'percentage_penalty_rate'
    ]

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['member', 'requested_amount', 'status', 'applied_date']

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'content']

    def approve_selected(self, request, queryset):
        # Bulk approval would need extra logic; we'll rely on custom view
        self.message_user(request, "Please use the approve button on each application.")
    approve_selected.short_description = "Approve selected (use detail view)"

    def reject_selected(self, request, queryset):
        queryset.update(status='Rejected')
    reject_selected.short_description = "Reject selected"