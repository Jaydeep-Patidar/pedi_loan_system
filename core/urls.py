from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/token/', views.token_obtain_pair, name='token_obtain_pair'),
    path('api/token/refresh/', views.token_refresh, name='token_refresh'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-change/', views.password_change, name='password_change'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Dashboard views (must match the names used in views.dashboard)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('member-dashboard/', views.member_dashboard, name='member_dashboard'),
    
    # Admin: Member management
    path('members/', views.member_list, name='member_list'),
    path('members/create/', views.member_create, name='member_create'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('members/<int:pk>/activate/', views.member_activate, name='member_activate'),
    
    # Pedi management
    path('pedis/', views.pedi_list, name='pedi_list'),
    path('pedis/payment-history/', views.pedi_payment_history_menu, name='pedi_payment_history_menu'),
    path('pedis/create/', views.pedi_create, name='pedi_create'),
    path('pedis/<int:pk>/edit/', views.pedi_edit, name='pedi_edit'),
    path('pedis/<int:pedi_id>/assign/', views.assign_members, name='assign_members'),
    path('pedis/<int:pedi_id>/payment-history/', views.pedi_payment_history, name='pedi_payment_history'),
    path('pedis/<int:pedi_id>/members/<int:member_id>/exit/', views.pedi_member_exit, name='pedi_member_exit'),
    path('pedis/<int:pedi_id>/members/<int:member_id>/exit-reject/', views.reject_member_exit_request, name='reject_member_exit_request'),
    path('member/pedis/<int:pedi_id>/exit-request/', views.member_pedi_exit_request, name='member_pedi_exit_request'),
    
    # Monthly payments
    path('payments/monthly/<int:pedi_id>/', views.monthly_payments, name='monthly_payments'),
    path('payments/', views.monthly_payments, name='monthly_payments_list'),
    
    # Loans
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/create/', views.loan_create, name='loan_create'),
    path('loans/<int:pk>/edit/', views.loan_edit, name='loan_edit'),
    path('loans/<int:loan_id>/admin-pay/', views.admin_loan_pay, name='admin_loan_pay'),
    path('loan/<int:loan_id>/pay-online/', views.loan_pay_online, name='loan_pay_online'),
    path('loan/payment/online-success/', views.loan_payment_online_success, name='loan_payment_online_success'),
    path('member/loan-payments/', views.loan_payment_history, name='loan_payment_history'),
    path('staff/loan-payments/', views.admin_loan_payments, name='admin_loan_payments'),    # Member views
    path('member/loans/', views.member_loans, name='member_loans'),
    path('member/payments/', views.member_payments, name='member_payments'),
    path('member/payment-history/', views.payment_history, name='payment_history'),
    path('member/make-payment/<int:payment_id>/', views.make_payment, name='make_payment'),
    path('member/payment-success/', views.payment_success, name='payment_success'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('export/members/', views.export_members_excel, name='export_members'),
    path('export/payments/', views.export_payments_excel, name='export_payments'),
    path('export/loans/', views.export_loans_excel, name='export_loans'),

    # Loan Application
    path('apply-loan/', views.apply_loan, name='apply_loan'),
    path('staff/loan-applications/', views.admin_loan_applications, name='admin_loan_applications'),
    path('staff/loan-application/<int:pk>/approve/', views.approve_loan_application, name='approve_loan_application'),
    path('staff/loan-application/<int:pk>/reject/', views.reject_loan_application, name='reject_loan_application'),
    path('staff/loan-settings/', views.admin_loan_settings, name='admin_loan_settings'),
    path('staff/loan-settings/history/', views.admin_loan_settings_history, name='admin_loan_settings_history'),

    # Notices
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/create/', views.notice_create, name='notice_create'),
    path('notices/<int:pk>/edit/', views.notice_edit, name='notice_edit'),
    path('notices/<int:pk>/delete/', views.notice_delete, name='notice_delete'),
    path('member/notices/', views.member_notices, name='member_notices'),
]
