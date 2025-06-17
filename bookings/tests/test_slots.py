from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from ..models import BookingSlot
from packages.models import Package

User = get_user_model()

class BookingSlotTests(APITestCase):
    def setUp(self):
        # Create test users
        self.staff_user = User.objects.create_user(
            username='staff@test.com',
            password='testpass123',
            mobile_number='9876543210',
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username='user@test.com',
            password='testpass123',
            mobile_number='9876543211'
        )
        
        # Create test package
        self.package = Package.objects.create(
            name='Test Package',
            description='Test Description',
            price=1000
        )
        
        # Create test slots
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        self.slot = BookingSlot.objects.create(
            date=self.tomorrow,
            time='10:00:00',
            total_slots=5,
            available_slots=5,
            package=self.package,
            is_holiday=False
        )

    def test_create_slot_as_staff(self):
        """Test creating a slot as staff user"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('booking-slot-list')
        data = {
            'date': (timezone.now().date() + timedelta(days=2)).isoformat(),
            'time': '14:00:00',
            'total_slots': 10,
            'package': self.package.id,
            'is_holiday': False
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['available_slots'], 10)

    def test_create_slot_as_normal_user(self):
        """Test that normal users cannot create slots"""
        self.client.force_authenticate(user=self.normal_user)
        url = reverse('booking-slot-list')
        data = {
            'date': (timezone.now().date() + timedelta(days=2)).isoformat(),
            'time': '14:00:00',
            'total_slots': 10,
            'package': self.package.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_slots_filtering(self):
        """Test slot listing with various filters"""
        self.client.force_authenticate(user=self.normal_user)
        url = reverse('booking-slot-list')

        # Create a holiday slot
        holiday_slot = BookingSlot.objects.create(
            date=self.tomorrow,
            time='11:00:00',
            total_slots=5,
            available_slots=5,
            package=self.package,
            is_holiday=True
        )

        # Test default filtering (no holidays)
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)
        
        # Test with holiday inclusion
        response = self.client.get(f'{url}?include_holidays=true')
        self.assertEqual(len(response.data), 2)

        # Test package filtering
        response = self.client.get(f'{url}?package_id={self.package.id}')
        self.assertEqual(len(response.data), 1)

        # Test date filtering
        response = self.client.get(f'{url}?date={self.tomorrow.isoformat()}')
        self.assertEqual(len(response.data), 1)

    def test_invalid_slot_creation(self):
        """Test validation rules for slot creation"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('booking-slot-list')

        # Test past date
        data = {
            'date': (timezone.now().date() - timedelta(days=1)).isoformat(),
            'time': '14:00:00',
            'total_slots': 10,
            'package': self.package.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date', response.data)

        # Test invalid total slots
        data['date'] = (timezone.now().date() + timedelta(days=1)).isoformat()
        data['total_slots'] = 0
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_slots', response.data)

    def test_update_slot(self):
        """Test updating a slot"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('booking-slot-detail', args=[self.slot.id])
        
        data = {
            'date': self.tomorrow.isoformat(),
            'time': '15:00:00',  # Changed time
            'total_slots': 8,    # Changed total slots
            'package': self.package.id,
            'is_holiday': True   # Changed holiday status
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['time'], '15:00:00')
        self.assertEqual(response.data['total_slots'], 8)
        self.assertEqual(response.data['is_holiday'], True) 