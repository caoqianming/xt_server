from django.urls import path, include
from .views import (StandardViewSet, StandardItemViewSet, CompanyViewSet,
                    AtaskViewSet, AtaskItemViewSet, AtaskTeamViewSet)
from rest_framework import routers

API_BASE_URL = 'api/audit/'
HTML_BASE_URL = 'audit/'

router = routers.DefaultRouter()
router.register("standard", StandardViewSet, basename='standard')
router.register("standarditem", StandardItemViewSet, basename='audit')
router.register("company", CompanyViewSet, basename='company')
router.register("atask", AtaskViewSet, basename='atask')
router.register("ataskteam", AtaskTeamViewSet, basename='ataskteam')
router.register("ataskitem", AtaskItemViewSet, basename="ataskitem")
urlpatterns = [
    path(API_BASE_URL, include(router.urls)),
]