from django.test import TestCase
from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from .models import User, Otp, StaffMember
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(mobile_number="1234567890")
        self.admin_user = User.objects.create(
            mobile_number="9999999999",
            is_staff=True,
            is_superuser=True
        )

    def test_register_or_login(self):
        url = reverse('register-or-login')
        data = {'mobile_number': '9876543210'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'OTP sent.')
        self.assertTrue(User.objects.filter(mobile_number='9876543210').exists())

    def test_verify_otp(self):
        # Create an OTP
        otp = Otp.objects.create(
            user=self.user,
            otp_code='123456',
            expire_at=timezone.now() + timezone.timedelta(minutes=5)
        )

        url = reverse('verify-otp')
        data = {
            'mobile_number': '1234567890',
            'otp_code': '123456'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_verify_otp_invalid(self):
        url = reverse('verify-otp')
        data = {
            'mobile_number': '1234567890',
            'otp_code': '000000'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(
            mobile_number="1234567890",
            first_name="Test",
            last_name="User"
        )
        self.token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')

    def test_get_profile(self):
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mobile_number'], '1234567890')

    def test_update_profile(self):
        url = reverse('profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'test@example.com',
            'gender': 'Male',
            'age': 25
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.email, 'test@example.com')

class StaffMemberTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create(
            mobile_number="9999999999",
            is_staff=True,
            is_superuser=True
        )
        self.normal_user = User.objects.create(mobile_number="1234567890")
        self.token = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')

    def test_register_staff_member(self):
        url = reverse('register-staff')
        data = {
            'mobile_number': '1234567890',
            'staff_code': 'STAFF001'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StaffMember.objects.filter(staff_code='STAFF001').exists())
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.is_staff_member)

    def test_register_staff_unauthorized(self):
        # Switch to non-admin user
        normal_token = RefreshToken.for_user(self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {normal_token.access_token}')
        
        url = reverse('register-staff')
        data = {
            'mobile_number': '1234567890',
            'staff_code': 'STAFF001'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
