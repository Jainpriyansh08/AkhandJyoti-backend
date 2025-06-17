import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import User, Otp
from django.utils import timezone
import json

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def mobile_number():
    return "9876543210"

@pytest.mark.django_db
class TestRegisterOrLoginView:
    def test_register_new_user(self, api_client, mobile_number):
        url = reverse('register-or-login')
        data = {'mobile_number': mobile_number}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert User.objects.filter(mobile_number=mobile_number).exists()
        assert Otp.objects.filter(user__mobile_number=mobile_number).exists()
        assert response.json()['detail'] == "OTP sent."

    def test_login_existing_user(self, api_client, mobile_number):
        # Create user first
        User.objects.create(mobile_number=mobile_number)
        
        url = reverse('register-or-login')
        data = {'mobile_number': mobile_number}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert Otp.objects.filter(user__mobile_number=mobile_number).exists()
        assert response.json()['detail'] == "OTP sent."

@pytest.mark.django_db
class TestVerifyOtpView:
    def test_verify_valid_otp(self, api_client, mobile_number):
        # Create user and OTP
        user = User.objects.create(mobile_number=mobile_number)
        otp_code = "123456"
        Otp.objects.create(
            user=user,
            otp_code=otp_code,
            expire_at=timezone.now() + timezone.timedelta(minutes=5)
        )
        
        url = reverse('verify-otp')
        data = {
            'mobile_number': mobile_number,
            'otp_code': otp_code
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert 'access' in response_data
        assert 'refresh' in response_data
        assert 'user' in response_data

    def test_verify_invalid_otp(self, api_client, mobile_number):
        # Create user but with different OTP
        user = User.objects.create(mobile_number=mobile_number)
        Otp.objects.create(
            user=user,
            otp_code="123456",
            expire_at=timezone.now() + timezone.timedelta(minutes=5)
        )
        
        url = reverse('verify-otp')
        data = {
            'mobile_number': mobile_number,
            'otp_code': "999999"  # Wrong OTP
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['detail'] == "Invalid or expired OTP."

    def test_verify_expired_otp(self, api_client, mobile_number):
        # Create user with expired OTP
        user = User.objects.create(mobile_number=mobile_number)
        otp_code = "123456"
        Otp.objects.create(
            user=user,
            otp_code=otp_code,
            expire_at=timezone.now() - timezone.timedelta(minutes=5)  # Expired
        )
        
        url = reverse('verify-otp')
        data = {
            'mobile_number': mobile_number,
            'otp_code': otp_code
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['detail'] == "Invalid or expired OTP." 