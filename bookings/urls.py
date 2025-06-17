from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingSlotViewSet, BookingOrderViewSet

router = DefaultRouter()
router.register(r'slots', BookingSlotViewSet, basename='booking-slot')
router.register(r'orders', BookingOrderViewSet, basename='bookingorder')

urlpatterns = [
    path('', include(router.urls)),
] 