from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PackageViewSet, PackageListView

router = DefaultRouter()
router.register('crud', PackageViewSet, basename='package')

urlpatterns = [
    path('', PackageListView.as_view(), name='package-list'),
    path('', include(router.urls)),
] 