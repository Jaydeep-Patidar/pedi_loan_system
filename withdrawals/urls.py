from django.urls import path
from . import views

urlpatterns = [
    path('member/withdrawal/request/', views.request_withdrawal, name='request_withdrawal'),
    path('member/withdrawal/requests/', views.withdrawal_requests_list, name='withdrawal_requests_list'),
    path('member/withdrawal/<int:pk>/', views.withdrawal_detail, name='withdrawal_detail'),
    path('staff/withdrawal/requests/', views.withdrawal_requests_admin_list, name='withdrawal_requests_admin_list'),
    path('staff/withdrawal/<int:pk>/', views.withdrawal_admin_detail, name='withdrawal_admin_detail'),
    path('staff/withdrawal/<int:pk>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
    path('staff/withdrawal/<int:pk>/reject/', views.reject_withdrawal, name='reject_withdrawal'),
    path('staff/withdrawal/transactions/', views.withdrawal_admin_list, name='withdrawal_admin_list'),
    path('staff/withdrawal/<int:pk>/process/', views.process_withdrawal_payment, name='process_withdrawal_payment'),
    path('withdrawal/<int:pk>/receipt/', views.withdrawal_receipt, name='withdrawal_receipt'),
]
