from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import BookingSlot, BookingOrder, BookingMember
from users.serializers import PatientSerializer, StaffMemberSerializer
from packages.serializers import PackageSerializer

class BookingSlotSerializer(serializers.ModelSerializer):
    package_details = PackageSerializer(source='package', read_only=True)
    
    class Meta:
        model = BookingSlot
        fields = [
            'id', 'date', 'time', 'total_slots', 'available_slots',
            'is_holiday', 'package', 'package_details', 'is_active',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['available_slots', 'created_at', 'modified_at']

    def validate(self, data):
        # Validate total slots
        if data.get('total_slots', 0) < 1:
            raise serializers.ValidationError({
                'total_slots': 'Total slots must be at least 1'
            })

        # Validate date is not in past
        if data.get('date'):
            if data['date'] < timezone.now().date():
                raise serializers.ValidationError({
                    'date': 'Cannot create slots for past dates'
                })

        return data

class BookingMemberSerializer(serializers.ModelSerializer):
    patient_details = PatientSerializer(source='patient', read_only=True)
    
    class Meta:
        model = BookingMember
        fields = ['id', 'booking', 'patient', 'patient_details', 'is_primary_contact', 
                 'created_at', 'modified_at']
        read_only_fields = ['created_at', 'modified_at', 'booking']

class BookingOrderSerializer(serializers.ModelSerializer):
    members = BookingMemberSerializer(many=True, read_only=True)
    booking_slot_details = BookingSlotSerializer(source='booking_slot', read_only=True)
    package_details = PackageSerializer(source='package', read_only=True)
    assisted_by_details = StaffMemberSerializer(source='assisted_by', many=True, read_only=True)
    
    class Meta:
        model = BookingOrder
        fields = ['id', 'booking_slot', 'booking_slot_details', 'account', 'package',
                 'package_details', 'status', 'total_amount', 'final_amount', 
                 'is_assisted_booking', 'assisted_by', 'assisted_by_details', 
                 'number_of_members', 'resource_hold_time', 'his_invoice_number', 
                 'members', 'created_at', 'modified_at']
        read_only_fields = ['status', 'total_amount', 'final_amount',
                           'resource_hold_time', 'his_invoice_number',
                           'created_at', 'modified_at', 'account']

    def validate(self, data):
        # Validate number of members
        if data.get('number_of_members', 0) < 1:
            raise serializers.ValidationError("Number of members must be at least 1")

        # Validate booking slot availability
        booking_slot = data.get('booking_slot')
        if booking_slot and booking_slot.available_slots < data.get('number_of_members', 1):
            raise serializers.ValidationError("Not enough slots available")

        return data 