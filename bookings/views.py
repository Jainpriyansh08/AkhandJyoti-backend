from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import BookingSlot
from .serializers import BookingSlotSerializer

# Create your views here.

class BookingSlotListView(generics.ListAPIView):
    serializer_class = BookingSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = BookingSlot.objects.filter(is_active=True)
        date = self.request.query_params.get('date')
        package = self.request.query_params.get('package')
        if date:
            queryset = queryset.filter(date=date)
        if package:
            queryset = queryset.filter(package_id=package)
        return queryset
