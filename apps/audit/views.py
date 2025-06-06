from django.shortcuts import render
from apps.utils.mixins import CustomListModelMixin, BulkCreateModelMixin, BulkUpdateModelMixin, BulkDestroyModelMixin
from apps.utils.viewsets import CustomModelViewSet, CustomGenericViewSet
from apps.audit.models import (Standard, StandardItem, Company, Atask, AtaskIssue, AtaskTeam, AtaskItem)
from apps.audit.serializers import (AtaskItemSerializer, StandardSerializer, StandardItemSerializer, 
                                    CompanySerializer, AtaskSerializer, AtaskTeamSerializer,
                                    AtaskItemCheckSerializer, AtaskIssueSerializer, AtaskDetailSerializer)
from rest_framework.exceptions import ParseError
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.response import Response
from .models import TKS_DICT
from apps.audit.service import daoru_standard
from django.conf import settings
from .filters import AtaskItemFilter, AtaskIssueFilter
# Create your views here.

class StandardViewSet(CustomModelViewSet):
    queryset = Standard.objects.all()
    serializer_class = StandardSerializer
    filterset_fields = ["to_type", "enabled"]
    search_fields = ["name"]

    @action(methods=['post'], detail=True, perms_map={'post': 'standard.update'})
    @transaction.atomic
    def daoru(self, request, *args, **kwargs):
        instance = self.get_object()
        path = request.data.get("path", "")
        if path:
            daoru_standard(settings.BASE_DIR + path, instance)
            return Response()
        raise ParseError("缺少path参数")

class StandardItemViewSet(CustomModelViewSet):
    perms_map = {"get": "*", "post": "standard.update", "put": "standard.update", "delete": "standard.update"}
    queryset = StandardItem.objects.all()
    serializer_class = StandardItemSerializer
    filterset_fields = ["standard", "id", "number"]
    search_fields = ["number", "content"]
    ordering = ["standard", "number"]

class CompanyViewSet(CustomModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filterset_fields = {
        "level": ["exact"]
    }
    search_fields = ["name"]
    ordering_fields = ["create_time", "update_time", "name"]
    ordering = ["name"]

    def add_info_for_list(self, data):
        for item in data:
            types = item["types"]
            types_name = ""
            for typei in types:
                types_name += TKS_DICT[typei] + "/"
            item["types_name"] = types_name
        return data
    
    def destroy(self, request, *args, **kwargs):
        ins:Company = self.get_object()
        if Atask.objects.filter(company=ins).exists():
            raise ParseError("该公司存在审计任务，无法删除")
        if Company.objects.filter(parent=ins).exists():
            raise ParseError("该公司存在子公司，无法删除")
        return super().destroy(request, *args, **kwargs)
class AtaskViewSet(CustomModelViewSet):
    perms_map = {"get": "*", "post": "atask.create", "put": "atask.update", "delete": "atask.delete"}
    queryset = Atask.objects.all()
    serializer_class = AtaskSerializer
    retrieve_serializer_class = AtaskDetailSerializer
    filterset_fields = ["company", "year", "standard", "standard__to_type", "state"]
    search_fields = ["company__name"]
    # data_filter = False
    # data_filter_field_user = "team_atask__member"
    
    def add_info_for_list(self, data):
        ids = [ins["id"] for ins in data]
        members_dict  = {}
        members = AtaskTeam.objects.filter(atask__id__in=ids).order_by("duty_type").select_related('member', 'atask')
        for member in members:
            if member.atask.id not in members_dict:
                members_dict[member.atask.id] = []
            members_dict[member.atask.id].append({
                "member_name": member.member.name,
                "duty_type": member.duty_type
            })
        # 然后更新data
        for item in data:
            task_id = item["id"]
            if task_id in members_dict:
                item["team"] = members_dict[task_id]
            else:
                item["team"] = []
        return data
    
    @action(methods=['get'], detail=False, perms_map={'get': '*'})
    def my(self, request, *args, **kwargs):
        qs = Atask.objects.exclude(state=Atask.S_WAIT).filter(team_atask__member=request.user)
        queryset = self.filter_queryset(qs)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.add_info_for_list(serializer.data)
            return self.get_paginated_response(data)
        serializer = self.get_serializer(queryset, many=True)
        data = self.add_info_for_list(serializer.data)
        return Response(data)
    
    @transaction.atomic
    def perform_create(self, serializer):
        ins:Atask = serializer.save()
        ins.init()
    
    def destroy(self, request, *args, **kwargs):
        ins:Atask = self.get_object()
        if ins.state != Atask.S_WAIT:
            raise ParseError("该任务已开始,禁止删除")
        if AtaskIssue.objects.filter(atask=self.get_object()).exists():
            raise ParseError("该任务下已存在审计数据,禁止删除")
        return super().destroy(request, *args, **kwargs)
    
    @action(methods=['put'], detail=True, perms_map={'post': "atask.update"})
    @transaction.atomic
    def state(self, request, *args, **kwargs):
        """变更状态"""
        state = request.data.get("state", None)
        if not state:
            raise ParseError("缺少参数")
        ins:Atask = self.get_object()
        # user = self.request.user
        # if ins.leader != user or ins.create_by != user:
        #     raise ParseError("非任务负责人/创建人禁止提交")
        # if ins.state != Atask.S_DOING:
        #     raise ParseError("该任务未开始,请勿重复操作")
        ins.state = state
        ins.save()
        return Response()

class AtaskTeamViewSet(BulkCreateModelMixin, BulkDestroyModelMixin, CustomGenericViewSet):
    perms_map = {"get": "*", "post": "atask.update", "delete": "atask.update"}
    queryset = AtaskTeam.objects.all()
    serializer_class = AtaskTeamSerializer

class AtaskItemViewSet(CustomListModelMixin, BulkUpdateModelMixin, CustomGenericViewSet):
    perms_map = {"get": "*", "put": "atask.check"}
    queryset = AtaskItem.objects.all()
    serializer_class = AtaskItemSerializer
    update_serializer_class = AtaskItemCheckSerializer
    select_related_fields = ["atask", "standarditem"]
    filterset_class = AtaskItemFilter
    ordering = ["atask", "standarditem__number"]

    def add_info_for_list(self, data):
        if isinstance(data, list):
            dataDict = {None: None}
            for item in data:
                dataDict[item["standarditem_"]["id"]] = item["id"]
                item["parent"] = dataDict.get(item["standarditem_"]["parent"], None)
        return data
    
    @transaction.atomic
    def perform_update(self, serializer):
        obj = self.get_object()
        if obj.atask.state != Atask.S_DOING:
            raise ParseError("该任务状态下不可操作")
        ins:AtaskItem = serializer.save()
        ins.cal_score(self.request.user)
    
    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('atask', None):
            pass
        else:
            raise ParseError("缺少查询参数")
        return super().list(request, *args, **kwargs)


class AtaskIssueViewSet(CustomModelViewSet):
    queryset = AtaskIssue.objects.all()
    serializer_class = AtaskIssueSerializer
    select_related_fields = ["atask", "standarditem", "create_by"]
    prefetch_related_fields = ["photos"]
    filterset_class = AtaskIssueFilter

    def get_queryset(self):
        if self.request.method == 'GET':
            if  (self.request.query_params.get("atask", None) 
                or self.request.query_params.get("standitem", None)
                or self.request.query_params.get("standitem_belong", None)):
                pass
            else:
                raise ParseError("缺少查询参数")
        return super().get_queryset()

    def check_perm(self, ins:AtaskIssue):
        ins:AtaskIssue = self.get_object()
        atask:Atask = ins.atask
        atask.check_do()
        if ins.create_by == self.request.user or ins.create_by == atask.leader:
            pass
        else:
            raise ParseError("仅创建人/负责人可修改")
        
    def update(self, request, *args, **kwargs):
        self.check_perm(ins=self.get_object())
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self.check_perm(ins=self.get_object())
        return super().destroy(request, *args, **kwargs)