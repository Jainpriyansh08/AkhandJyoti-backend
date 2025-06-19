from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    RazorpayWebhookView,
    PaymentHistoryView
)

app_name = 'payments'

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='initiate_payment'),
    path('status/', PaymentStatusView.as_view(), name='payment_status'),
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay_webhook'),
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
] 