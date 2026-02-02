from django_filters import rest_framework as filters
from .models import Dept, User
from apps.utils.queryset import get_child_queryset2
from rest_framework.exceptions import ParseError


class UserFilterSet(filters.FilterSet):
    ubelong_dept__name = filters.CharFilter(label='归属于该部门及以下(按名称)', method='filter_ubelong_dept__name')
    ubelong_dept = filters.CharFilter(label='归属于该部门及以下', method='filter_ubelong_dept')
    has_perm = filters.CharFilter(label='拥有指定权限标识', method='filter_has_perm')

    class Meta:
        model = User
        fields = {
            'name': ['exact', 'contains'],
            'is_deleted': ['exact'],
            'posts': ['exact'],
            'post': ['exact'],
            'belong_dept': ['exact'],
            'depts': ['exact'],
            'type': ['exact', 'in'],
            'belong_dept__name': ['exact'],
            'depts__name': ["exact", "contains"],
            'posts__name': ["exact", "contains"],
            'posts__code': ["exact", "contains"], 
        }
    
    def filter_ubelong_dept__name(self, queryset, name, value):
        try:
            depts = get_child_queryset2(Dept.objects.get(name=value))
        except Exception as e:
            raise ParseError(f"部门名称错误: {value} {str(e)}")
        return queryset.filter(belong_dept__in=depts)
    
    def filter_ubelong_dept(self, queryset, name, value):
        try:
            depts = get_child_queryset2(Dept.objects.get(id=value))
        except Exception as e:
            raise ParseError(f"部门ID错误: {value} {str(e)}")
        return queryset.filter(belong_dept__in=depts)
    
    def filter_has_perm(self, queryset, name, value):
        return queryset.filter(up_user__post__pr_post__role__perms__codes__contains=value)


class DeptFilterSet(filters.FilterSet):

    class Meta:
        model = Dept
        fields = {
            'type': ['exact', 'in'],
            'name': ['exact', 'in', 'contains'],
            "parent": ['exact', 'isnull'],
        }
