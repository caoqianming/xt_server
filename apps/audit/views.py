from django.shortcuts import render
from apps.utils.mixins import CustomListModelMixin, UpdateModelMixin
from apps.utils.viewsets import CustomModelViewSet, CustomGenericViewSet
from apps.audit.models import (Standard, StandardItem, Company, Atask, AtaskIssue, AtaskTeam, AtaskItem)
from apps.audit.serializers import (AtaskItemSerializer, StandardSerializer, StandardItemSerializer, 
                                    CompanySerializer, AtaskSerializer, 
                                    AtaskItemCheckSerializer, AtaskIssueSerializer)
from rest_framework.exceptions import ParseError
from apps.utils.permission import has_perm
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.response import Response
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
    ordering = ["standard", "cate", "number"]

class CompanyViewSet(CustomModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filterset_fields = {
        "level": ["exact"],
        "types": ["contains"]
    }
    search_fields = ["name"]

class AtaskViewSet(CustomModelViewSet):
    perms_map = {"get": "atask.view", "post": "atask.create", "put": "atask.update", "delete": "atask.delete"}
    queryset = Atask.objects.all()
    serializer_class = AtaskSerializer
    filterset_fields = ["company", "year", "standard", "standard__type", "state"]
    search_fields = ["company__name"]
    data_filter = True
    data_filter_field_user = "team_atask__member"

    def add_info_for_list(self, data):
        return data
    
    def destroy(self, request, *args, **kwargs):
        if AtaskIssue.objects.filter(ataskitem__atask=self.get_object()).exists():
            raise ParseError("该任务下已存在审计数据,禁止删除")
        return super().destroy(request, *args, **kwargs)
    
    @action(methods=['post'], detail=True, perms_map={'post': 'atask.update'})
    @transaction.atomic
    def start(self, request, *args, **kwargs):
        """开始审计"""
        ins:Atask = self.get_object()
        if ins.state != Atask.S_WAIT:
            raise ParseError("该任务已开始,请勿重复操作")
        ins.state = Atask.S_DOING
        ins.save()
        for st in StandardItem.objects.filter(standard=ins.standard).order_by("number"):
            AtaskItem.objects.create(atask=ins, standarditem=st)
        return Response()
    
    @action(methods=['post'], detail=True, perms_map={'post': "atask.submit"})
    @transaction.atomic
    def submit(self, request, *args, **kwargs):
        """提交任务"""
        ins:Atask = self.get_object()
        user = self.request.user
        if ins.leader != user or ins.create_by != user:
            raise ParseError("非任务负责人/创建人禁止提交")
        if ins.state != Atask.S_DOING:
            raise ParseError("该任务未开始,请勿重复操作")
        ins.state = Atask.S_DONE
        ins.save()
        return Response()

class AtaskItemViewSet(CustomListModelMixin, UpdateModelMixin, CustomGenericViewSet):
    perms_map = {"get": "*", "put": "atask.check"}
    queryset = AtaskItem.objects.all()
    serializer_class = AtaskItemSerializer
    update_serializer_class = AtaskItemCheckSerializer
    select_related_fields = ["atask", "standard"]
    filterset_fields = ["atask", "standarditem", "check_user"]
    ordering = ["standarditem__number", "create_time"]

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.atask.state != Atask.S_DOING:
            raise ParseError("该任务状态下不可操作")
        return super().update(request, *args, **kwargs)
    def get_queryset(self):
        if self.request.query_params.get("atask", None):
            pass
        else:
            raise ParseError("缺少atask参数")
        return super().get_queryset()
    

class AtaskIssueViewSet(CustomModelViewSet):
    queryset = AtaskIssue.objects.all()
    serializer_class = AtaskIssueSerializer
    filterset_fields = ["ataskitem", "ataskitem__atask"]

    def get_queryset(self):
        if (self.request.query_params.get("ataskitem", None) 
            or self.request.query_params.get("ataskitem__atask", None)):
            pass
        else:
            raise ParseError("缺少查询参数")
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        ins:AtaskIssue = self.get_object()
        ins.ataskitem.atask.check_do()
        return super().create(request, *args, **kwargs)
    def update(self, request, *args, **kwargs):
        ins:AtaskIssue = self.get_object()
        atask:Atask = ins.ataskitem.atask
        atask.check_do()
        if ins.create_by != self.request.user or ins.create_by != atask.leader:
            raise ParseError("仅创建人/负责人可修改")
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        ataskitem:AtaskItem = instance.ataskitem
        ataskitem.atask.check_do()
        return super().perform_destroy(instance)