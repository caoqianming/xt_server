from django_filters import rest_framework as filters
from .models import AtaskItem, AtaskIssue, StandardItem
from apps.utils.queryset import get_child_queryset2

class AtaskItemFilter(filters.FilterSet):
    class Meta:
        model = AtaskItem
        fields = {
            "atask": ["exact"],
            "standarditem": ["exact"],
            "check_user": ["exact"],
            "standarditem__level": ["exact"],
            "standarditem__parent": ["exact", "isnull"]
        }

class AtaskIssueFilter(filters.FilterSet):
    ataskitem_belong = filters.CharFilter(method="filter_ataskitem_belong")
    class Meta:
        model = AtaskIssue
        fields = {
            "ataskitem": ["exact"],
            "ataskitem__atask": ["exact"],
        }

    def filter_ataskitem_belong(self, queryset, name, value):
        standarditem = AtaskItem.objects.get(pk=value).standarditem
        return queryset.filter(ataskitem__standarditem__in=get_child_queryset2(standarditem))