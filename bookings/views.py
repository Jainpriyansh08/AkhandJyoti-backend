from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import BookingSlot, BookingOrder, BookingMember
from .serializers import (
    BookingSlotSerializer,
    BookingOrderSerializer,
    BookingMemberSerializer
)

# Create your views here.

class IsStaffMemberOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow staff members to create/edit slots.
    """
    def has_permission(self, request, view):
        # Allow read-only access for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Write permissions only for staff
        return request.user and (request.user.is_staff or request.user.is_staff_member)

class BookingSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing booking slots.
    """
    queryset = BookingSlot.objects.all()
    serializer_class = BookingSlotSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        """
        Filter slots based on query parameters:
        - date: specific date
        - package_id: specific package
        - include_holidays: whether to include holiday slots
        - include_inactive: whether to include inactive slots
        - future_only: whether to only show future slots (default True)
        """
        queryset = BookingSlot.objects.all()
        
        # Get query parameters
        date = self.request.query_params.get('date')
        package_id = self.request.query_params.get('package_id')
        include_holidays = self.request.query_params.get('include_holidays', 'false').lower() == 'true'
        include_inactive = self.request.query_params.get('include_inactive', 'false').lower() == 'true'
        future_only = self.request.query_params.get('future_only', 'true').lower() == 'true'

        # Apply filters
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        if not include_holidays:
            queryset = queryset.filter(is_holiday=False)
        
        if future_only:
            queryset = queryset.filter(date__gte=timezone.now().date())

        if date:
            queryset = queryset.filter(date=date)
        
        if package_id:
            queryset = queryset.filter(package_id=package_id)

        return queryset.order_by('date', 'time')

    def perform_create(self, serializer):
        """
        Set available_slots equal to total_slots when creating.
        """
        serializer.save(available_slots=serializer.validated_data['total_slots'])

class BookingOrderViewSet(viewsets.ModelViewSet):
    serializer_class = BookingOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_staff_member:
            return BookingOrder.objects.all()
        return BookingOrder.objects.filter(account=user)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        
        # Check if booking can be confirmed
        if booking.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Only IN_PROGRESS bookings can be confirmed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if resource hold has expired
        if (booking.resource_hold_time and 
            booking.resource_hold_time + timedelta(minutes=15) < timezone.now()):
            booking.status = 'FAILED'
            booking.save()
            return Response(
                {"detail": "Resource hold has expired"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if all required members are added
        if booking.members.count() != booking.number_of_members:
            return Response(
                {"detail": "All members must be added before confirmation"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Confirm the booking
        booking.status = 'CONFIRMED'
        booking.save()
        
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()
        
        if booking.status != 'CONFIRMED':
            return Response(
                {"detail": "Only CONFIRMED bookings can be completed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'COMPLETED'
        booking.save()
        
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        
        if booking.status not in ['IN_PROGRESS', 'CONFIRMED']:
            return Response(
                {"detail": "Cannot cancel booking in current status"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Release the held slots
            booking_slot = booking.booking_slot
            booking_slot.available_slots += booking.number_of_members
            booking_slot.save()
            
            # Update booking status
            booking.status = 'CANCELLED'
            booking.save()
            
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        booking = self.get_object()
        
        # Check if booking is in valid state
        if booking.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Can only add members to IN_PROGRESS bookings"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if we've reached member limit
        if booking.members.count() >= booking.number_of_members:
            return Response(
                {"detail": "Cannot add more members than specified"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Create member
        serializer = BookingMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(booking=booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def generate_his_invoice(self, request, pk=None):
        booking = self.get_object()
        
        # Check if booking is confirmed
        if booking.status != 'CONFIRMED':
            return Response(
                {"detail": "Can only generate HIS invoice for confirmed bookings"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if invoice is already generated
        if booking.his_invoice_generated:
            return Response(
                {"detail": "HIS invoice already generated"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Generate invoice
        invoice_number = request.data.get('invoice_number')
        if not invoice_number:
            return Response(
                {"detail": "Invoice number is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        booking.his_invoice_number = invoice_number
        booking.his_invoice_generated = True
        booking.save()
        
        return Response(self.get_serializer(booking).data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = self.get_queryset().filter(
            account=request.user
        ).order_by('-created_at')
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
