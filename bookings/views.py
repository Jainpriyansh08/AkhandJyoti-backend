from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import BookingSlot, BookingOrder, BookingMember, Coupon
from .serializers import (
    BookingSlotSerializer,
    BookingOrderSerializer,
    BookingMemberSerializer,
    ApplyCouponSerializer
)
from django.core.exceptions import ValidationError

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
    
    def get_permissions(self):
        """
        Allow unauthenticated access to list and retrieve.
        Require staff permissions for create, update, delete.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
            self.authentication_classes = []  # No authentication required for list and retrieve
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Filter slots based on query parameters:
        - date: specific date (YYYY-MM-DD)
        - package_id: specific package
        - include_holidays: whether to include holiday slots (default: false)
        - include_inactive: whether to include inactive slots (default: false)
        - future_only: whether to only show future slots (default: true)
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
    queryset = BookingOrder.objects.all()
    serializer_class = BookingOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BookingOrder.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        booking_slot = serializer.validated_data['booking_slot']
        serializer.save(
            user=self.request.user,
            package=booking_slot.package
        )

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
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot add members to a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if booking_order.members.count() >= booking_order.number_of_members:
            return Response(
                {"detail": "Maximum number of members already added"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = BookingMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(booking=booking_order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def apply_coupon(self, request, pk=None):
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot apply coupon to a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApplyCouponSerializer(
            data=request.data,
            context={'booking_order': booking_order}
        )
        
        if serializer.is_valid():
            return Response({
                'discount_applied': serializer.validated_data['discount'],
                'final_amount': booking_order.final_amount
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_coupon(self, request, pk=None):
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot remove coupon from a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        coupon_code = request.data.get('coupon_code')
        if not coupon_code:
            return Response(
                {"detail": "Coupon code is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            discount_removed = booking_order.remove_coupon(coupon_code)
            return Response({
                'discount_removed': discount_removed,
                'final_amount': booking_order.final_amount
            })
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot process payment for a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if booking_order.members.count() != booking_order.number_of_members:
            return Response(
                {"detail": "Please add all members before making payment"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Here you would integrate with your payment gateway
        # For now, we'll just mark the booking as confirmed
        booking_order.status = 'CONFIRMED'
        booking_order.save()
        
        serializer = self.get_serializer(booking_order)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = self.get_queryset().filter(
            user=request.user
        ).order_by('-created_at')
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
