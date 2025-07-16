from django_filters import rest_framework as filters
from .models import AtaskItem, AtaskIssue, StandardItem
from apps.utils.queryset import get_child_queryset2

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
        st = StandardItem.objects.get(pk=value)
        return queryset.filter(standarditem__parent=st.parent)

class AtaskIssueFilter(filters.FilterSet):
    # ataskitem_belong = filters.CharFilter(method="filter_ataskitem_belong")
    standarditem_belong = filters.CharFilter(method="filter_standarditem_belong")
    class Meta:
        model = AtaskIssue
        fields = {
            "atask": ["exact"],
            "standarditem": ["exact"],
            "create_by": ["exact"],
        }

    def filter_standarditem_belong(self, queryset, name, value):
        standarditem = StandardItem.objects.get(pk=value)
        return queryset.filter(standarditem__in=get_child_queryset2(standarditem))
    
    # def filter_ataskitem_belong(self, queryset, name, value):
    #     standarditem = AtaskItem.objects.get(pk=value).standarditem
    #     return queryset.filter(ataskitem__standarditem__in=get_child_queryset2(standarditem))