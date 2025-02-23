from django.shortcuts import render
from apps.utils.viewsets import CustomModelViewSet
from apps.audit.models import (Standard, StandardItem, Company)
from apps.audit.serializers import (StandardSerializer, StandardItemSerializer, CompanySerializer)
# Create your views here.

class StandardViewSet(CustomModelViewSet):
    queryset = Standard.objects.all()
    serializer_class = StandardSerializer
    filterset_fields = ["to_type", "enabled"]
    search_fields = ["name"]


class StandardItemViewSet(CustomModelViewSet):
    perms_map = {"get": "*", "post": "standard.update", "put": "standard.update", "delete": "standard.update"}
    queryset = StandardItem.objects.all()
    serializer_class = StandardItemSerializer
    filterset_fields = ["standard"]
    search_fields = ["number", "content"]
    ordering = ["standard", "number"]

class CompanyViewSet(CustomModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filterset_fields = {
        "level": ["exact"],
        "types": ["contains"]
    }
    search_fields = ["name"]