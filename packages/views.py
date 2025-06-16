from django.shortcuts import render
from rest_framework import generics
from .models import Package
from .serializers import PackageSerializer

# Create your views here.

class PackageListView(generics.ListAPIView):
    queryset = Package.objects.filter(is_active=True)
    serializer_class = PackageSerializer
