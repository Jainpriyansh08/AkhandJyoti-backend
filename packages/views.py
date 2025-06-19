from django.shortcuts import render
from rest_framework import generics, filters, viewsets, status
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, NumberFilter, CharFilter
from rest_framework.response import Response
from .models import Package
from .serializers import PackageSerializer
from rest_framework.decorators import action

# Create your views here.

class PackageFilter(FilterSet):
    min_price = NumberFilter(field_name="discounted_amount", lookup_expr='gte')
    max_price = NumberFilter(field_name="discounted_amount", lookup_expr='lte')
    min_discount = NumberFilter(field_name="discount_percentage", lookup_expr='gte')
    name = CharFilter(field_name="name", lookup_expr='icontains')
    description = CharFilter(field_name="description", lookup_expr='icontains')

    class Meta:
        model = Package
        fields = ['is_active', 'min_price', 'max_price', 'min_discount', 'name', 'description']

class PackageListView(generics.ListAPIView):
    serializer_class = PackageSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PackageFilter
    search_fields = ['name', 'description']
    ordering_fields = ['base_amount', 'discounted_amount', 'discount_percentage', 'created_at', 'name']
    ordering = ['base_amount']  # default ordering

    def get_queryset(self):
        """
        Get the list of packages with filtering
        """
        return Package.objects.all()

class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [AllowAny]
