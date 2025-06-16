from django.urls import path
from .views import BookingSlotListView

urlpatterns = [
    path('slots/', BookingSlotListView.as_view(), name='booking-slot-list'),
] 