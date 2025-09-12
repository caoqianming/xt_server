
from django.core.cache import cache
from django.http import StreamingHttpResponse, Http404
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.system.models import DataFilter, Dept
from apps.utils.mixins import (MyLoggingMixin, BulkCreateModelMixin, BulkUpdateModelMixin, 
                                BulkDestroyModelMixin, CustomListModelMixin, 
                                CustomRetrieveModelMixin, ComplexQueryMixin)
from apps.utils.permission import ALL_PERMS, RbacPermission, get_user_perms_map
from apps.utils.queryset import get_child_queryset2, get_child_queryset_u
from apps.utils.serializers import ComplexSerializer
from rest_framework.throttling import UserRateThrottle
from drf_yasg.utils import swagger_auto_schema
import json
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction


class CustomGenericViewSet(MyLoggingMixin, GenericViewSet):
    """
    增强的GenericViewSet
    """
    _initialized = False
    perms_map = None  # 权限标识
    throttle_classes = [UserRateThrottle]
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    ordering_fields = '__all__'
    ordering = '-create_time'
    create_serializer_class = None
    update_serializer_class = None
    partial_update_serializer_class = None
    list_serializer_class = None
    retrieve_serializer_class = None
    select_related_fields = []
    prefetch_related_fields = []
    permission_classes = [IsAuthenticated & RbacPermission]
    data_filter = False  # 数据权限过滤是否开启(需要RbacPermission)
    data_filter_field = 'belong_dept'
    hash_k = None
    cache_seconds = 5   # 接口缓存时间默认5秒
    filterset_fields = select_related_fields

    def __new__(cls, *args, **kwargs):
        """
        第一次实例化时，将权限标识添加到全局权限标识列表中
        """
        if not cls._initialized:
            if cls.perms_map is None:
                basename = kwargs["basename"]
                cls.perms_map = {'get': '*', 'post': '{}.create'.format(basename), 'put': '{}.update'.format(
                    basename), 'patch': '{}.update'.format(basename), 'delete': '{}.delete'.format(basename)}
            for _, v in cls.perms_map.items():
                if v not in ALL_PERMS and v != '*':
                    ALL_PERMS.append(v)
            cls._initialized = True
        return super().__new__(cls)
    
    def dispatch(self, request, *args, **kwargs):
        # 判断是否需要事务
        if self._should_use_transaction(request):
            with transaction.atomic():
                return super().dispatch(request, *args, **kwargs)
        else:
            return super().dispatch(request, *args, **kwargs)
    
    def _should_use_transaction(self, request):
        """判断当前请求是否需要事务"""
        # 标准的写操作需要事务
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            # 但还要看具体是哪个action
            action = self.action_map.get(request.method.lower(), {}).get(request.method.lower())
            if action in ['create', 'update', 'partial_update', 'destroy']:
                return True
        
        # 自定义的action：可以通过在action方法上添加装饰器或特殊属性来判断
        action = getattr(self, self.action, None) if self.action else None
        if action and getattr(action, 'requires_transaction', False):
            return True
            
        return False
        
    def finalize_response(self, request, response, *args, **kwargs):
        if self.hash_k and self.cache_seconds:
            cache.set(self.hash_k, response.data,
                      timeout=self.cache_seconds)  # 将结果存入缓存，设置超时时间
        return super().finalize_response(request, response, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        cache_seconds = getattr(
            self, f"{self.action}_cache_seconds", getattr(self, 'cache_seconds', 0))
        if cache_seconds:
            self.cache_seconds = cache_seconds
            rdata = {}
            rdata['request_method'] = request.method
            rdata['request_path'] = request.path
            rdata['request_data'] = request.data
            rdata['request_query'] = request.query_params.dict()
            rdata['request_userid'] = request.user.id
            self.hash_k = hash(json.dumps(rdata))
            hash_v_e = cache.get(self.hash_k, None)
            if hash_v_e is None:
                cache.set(self.hash_k, 'o', self.cache_seconds)
            elif hash_v_e == 'o':  # 说明请求正在处理
                raise ParseError(f'请求忽略,请{self.cache_seconds}秒后重试')
            elif hash_v_e:
                return Response(hash_v_e)

    def get_object(self, force_lock=False):
        """
        智能加锁的get_object
        - 只读请求：普通查询
        - 非只读请求且在事务中：加锁查询
        - 非只读请求但不在事务中：普通查询（带警告）
        """
        # 只读方法列表
        read_only_methods = ['GET', 'HEAD', 'OPTIONS']
        
        if self.request.method not in read_only_methods and connection.in_atomic_block:
            if force_lock:
                raise ParseError("当前操作需要在事务中进行，请使用事务装饰器")
            # 非只读请求且在事务中：加锁查询
            queryset = self.filter_queryset(self.get_queryset())
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            
            try:
                obj = queryset.select_for_update().get(**filter_kwargs)
                self.check_object_permissions(self.request, obj)
                return obj
            except ObjectDoesNotExist:
                raise Http404
        else:
            # 其他情况：普通查询
            return super().get_object()
    
    def get_serializer_class(self):
        action_serializer_name = f"{self.action}_serializer_class"
        action_serializer_class = getattr(self, action_serializer_name, None)
        if action_serializer_class:
            return action_serializer_class
        return super().get_serializer_class()

    def get_queryset_custom(self, queryset):
        """
        自定义过滤方法可复写
        """
        if self.action in ["list", "retrieve", "create", "update", "partial_update", "destroy"]:
            return queryset
        elif hasattr(self, f'get_queryset_{self.action}'):
            return getattr(self, f'get_queryset_{self.action}')(queryset)
        return queryset

    def filter_queryset(self, queryset):
        # 用于性能优化
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        queryset = super().filter_queryset(queryset)
        # 如果带有with_children查询, 出于优化需要应自动过滤掉一些内容
        # if (self.request.query_params.get("with_children", "no") in ["yes", "count"] 
        #     and self.request.query_params.get("parent", None) is None):
        #     queryset = queryset.filter(parent=None)
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = self.get_queryset_custom(queryset)
        if self.data_filter:
            user = self.request.user
            if user.is_superuser:
                return queryset
            user_perms_map = get_user_perms_map(self.request.user)
            if isinstance(user_perms_map, dict):
                if hasattr(self, 'perms_map'):
                    perms_map = self.perms_map
                    action_str = perms_map.get(
                        self.request._request.method.lower(), None)
                    if '*' in perms_map:
                        return queryset
                    elif action_str == '*':
                        return queryset
                    elif action_str in user_perms_map:
                        new_queryset = queryset.none()
                        for dept_id, data_range in user_perms_map[action_str].items():
                            dept = Dept.objects.get(id=dept_id)
                            if data_range == DataFilter.ALL:
                                return queryset
                            elif data_range == DataFilter.SAMELEVE_AND_BELOW:
                                queryset = self.filter_s_a_b(queryset, dept)
                            elif data_range == DataFilter.THISLEVEL_AND_BELOW:
                                queryset = self.filter_t_a_b(queryset, dept)
                            elif data_range == DataFilter.THISLEVEL:
                                queryset = self.filter_t(queryset, dept)
                            elif data_range == DataFilter.MYSELF:
                                queryset = queryset.filter(create_by=user)
                            new_queryset = new_queryset | queryset
                        return new_queryset
                    else:
                        return queryset.none()
        return queryset

    def filter_s_a_b(self, queryset, dept):
        """过滤同级及以下, 可重写
        """
        if hasattr(queryset.model, 'belong_dept'):
            if dept.parent:
                belong_depts = get_child_queryset2(dept.parent)
            else:
                belong_depts = get_child_queryset2(dept)
            whereis = {self.data_filter_field + '__in': belong_depts}
            queryset = queryset.filter(**whereis)
            return queryset
        return queryset.filter(create_by=self.request.user)

    def filter_t_a_b(self, queryset, dept):
        """过滤本级及以下, 可重写
        """
        if hasattr(queryset.model, 'belong_dept'):
            belong_depts = get_child_queryset2(dept)
            whereis = {self.data_filter_field + '__in': belong_depts}
            queryset = queryset.filter(**whereis)
            return queryset
        return queryset.filter(create_by=self.request.user)

    def filter_t(self, queryset, dept):
        """过滤本级, 可重写
        """
        if hasattr(queryset.model, 'belong_dept'):
            whereis = {self.data_filter_field: dept}
            queryset = queryset.filter(whereis)
            return queryset
        return queryset.filter(create_by=self.request.user)


class CustomModelViewSet(BulkCreateModelMixin, BulkUpdateModelMixin, CustomListModelMixin,
                         CustomRetrieveModelMixin, BulkDestroyModelMixin, ComplexQueryMixin, CustomGenericViewSet):
    """
    增强的ModelViewSet
    """