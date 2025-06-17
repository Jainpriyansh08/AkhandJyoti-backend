from django.urls import path
from .views import (
    RegisterOrLoginView, 
    VerifyOtpView, 
    ProfileView,
    RegisterStaffMemberView,
    LogoutView,
    PatientRegistrationView
)

urlpatterns = [
    path('register-or-login/', RegisterOrLoginView.as_view(), name='register-or-login'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('register-staff/', RegisterStaffMemberView.as_view(), name='register-staff'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register-patients/', PatientRegistrationView.as_view(), name='register-patients'),
] 