from django.urls import path, include
from .views import (StandardViewSet, StandardItemViewSet, CompanyViewSet)
from rest_framework import routers

API_BASE_URL = 'api/audit/'
HTML_BASE_URL = 'audit/'

router = routers.DefaultRouter()
router.register("standard", StandardViewSet, basename='standard')
router.register("standard_item", StandardItemViewSet, basename='audit')
router.register("company", CompanyViewSet, basename='company')
urlpatterns = [
    path(API_BASE_URL, include(router.urls)),
]