from django.urls import path
from .views import RegisterOrLoginView, VerifyOtpView

urlpatterns = [
    path('register-or-login/', RegisterOrLoginView.as_view(), name='register-or-login'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
] 