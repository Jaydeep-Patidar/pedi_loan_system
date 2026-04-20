from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Dashboard views (must match the names used in views.dashboard)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('member-dashboard/', views.member_dashboard, name='member_dashboard'),
    
    # Admin: Member management
    path('members/', views.member_list, name='member_list'),
    path('members/create/', views.member_create, name='member_create'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    
    # Pedi management
    path('pedis/', views.pedi_list, name='pedi_list'),
    path('pedis/create/', views.pedi_create, name='pedi_create'),
    path('pedis/<int:pk>/edit/', views.pedi_edit, name='pedi_edit'),
    path('pedis/<int:pedi_id>/assign/', views.assign_members, name='assign_members'),
    
    # Monthly payments
    path('payments/monthly/<int:pedi_id>/', views.monthly_payments, name='monthly_payments'),
    path('payments/', views.monthly_payments, name='monthly_payments_list'),
    
    # Loans
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/create/', views.loan_create, name='loan_create'),
    path('loans/<int:pk>/edit/', views.loan_edit, name='loan_edit'),
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
]
