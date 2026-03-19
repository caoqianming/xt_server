from django_filters import rest_framework as filters
from .models import AtaskItem, AtaskIssue, StandardItem
from apps.utils.queryset import get_child_queryset2
import logging

myLogger = logging.getLogger('log')

class AtaskItemFilter(filters.FilterSet):
    standarditem_p = filters.CharFilter(method="filter_standarditem_p")
    class Meta:
        model = AtaskItem
        fields = {
            "atask": ["exact"],
            "standarditem": ["exact"],
            "check_user": ["exact"],
            "standarditem__level": ["exact"],
            "standarditem__parent": ["exact", "isnull"]
        }

    def filter_standarditem_p(self, queryset, name, value):
        try:
            st = StandardItem.objects.get(pk=value)
        except StandardItem.DoesNotExist:
            return queryset.filter(standarditem__parent__isnull=True)
        return queryset.filter(standarditem__parent=st.parent)
        

class AtaskIssueFilter(filters.FilterSet):
    # ataskitem_belong = filters.CharFilter(method="filter_ataskitem_belong")
    standarditem_belong = filters.CharFilter(method="filter_standarditem_belong")
    create_by_name = filters.CharFilter(method="filter_create_by_name")
    ids = filters.CharFilter(method="filter_ids")
    class Meta:
        model = AtaskIssue
        fields = {
            "atask": ["exact"],
            "id": ["exact"],
            "standarditem": ["exact"],
            "create_by": ["exact"],
            "standarditem__number": ["exact", "startswith"],
            "standarditem__standard__to_type": ["exact"],
            "standarditem__level": ["exact"],
            "content": ["contains"],
            "atask__company__parent": ["exact"],
            "atask__company": ["exact"],
            "risk_level": ["exact"],
        }

    def filter_standarditem_belong(self, queryset, name, value):
        standarditem = StandardItem.objects.get(pk=value)
        return queryset.filter(standarditem__in=get_child_queryset2(standarditem))

    def filter_create_by_name(self, queryset, name, value):
        return queryset.filter(create_by__name__icontains=value)

    def filter_ids(self, queryset, name, value):
        ids = [item.strip() for item in value.split(",") if item.strip()]
        if not ids:
            return queryset.none()
        return queryset.filter(id__in=ids)
    
    # def filter_ataskitem_belong(self, queryset, name, value):
    #     standarditem = AtaskItem.objects.get(pk=value).standarditem
    #     return queryset.filter(ataskitem__standarditem__in=get_child_queryset2(standarditem))
