from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet, OrderViewSet

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet)
router.register(r'orders', OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]