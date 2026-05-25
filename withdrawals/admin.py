from django.contrib import admin
from .models import WithdrawalRequest, Withdrawal


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'member', 'requested_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['member__user__username', 'member__user__first_name', 'member__user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'calculated_amount']
    fields = ['member', 'requested_amount', 'calculated_amount', 'status', 'remarks', 'created_at', 'updated_at']


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['id', 'member', 'withdrawal_amount', 'status', 'payment_method', 'processed_at']
    list_filter = ['status', 'payment_method', 'processed_at']
    search_fields = ['member__user__username', 'member__user__first_name', 'member__user__last_name']
    readonly_fields = ['created_at', 'processed_at']
    fields = [
        'member', 'withdrawal_request', 'total_paid_amount', 'total_penalties_paid', 'withdrawal_amount',
        'payment_method', 'transaction_reference', 'status', 'processed_by', 'processed_at',
        'reason', 'notes', 'created_at'
    ]

    def reject_selected(self, request, queryset):
        queryset.update(status='Rejected')
    reject_selected.short_description = "Reject selected"
