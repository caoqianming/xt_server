from django.shortcuts import render
from apps.utils.mixins import CustomListModelMixin, BulkCreateModelMixin, BulkUpdateModelMixin, BulkDestroyModelMixin
from apps.utils.viewsets import CustomModelViewSet, CustomGenericViewSet
from apps.audit.models import (Standard, StandardItem, Company, Atask, AtaskIssue, AtaskTeam, AtaskItem, AtaskProblem)
from apps.audit.serializers import (AtaskItemSerializer, StandardSerializer, StandardItemSerializer, 
                                    CompanySerializer, AtaskSerializer, AtaskTeamSerializer,
                                    AtaskItemCheckSerializer, AtaskIssueSerializer, AtaskDetailSerializer, 
                                    AtaskIssueExportSerializer, AtaskProblemSerializer, AtaskIssueExportWithImgSerializer)
from rest_framework.exceptions import ParseError
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.response import Response
from .models import TKS_DICT, R_LEVEL_DICT
from apps.audit.service import daoru_standard, daoru_issue, sendMail
from django.conf import settings
from .filters import AtaskItemFilter, AtaskIssueFilter
from rest_framework import serializers
from apps.audit.service_2 import export_issue_docx, export_atask_report
from apps.utils.export import export_excel
from apps.audit.m_ppt import export_pptx
from apps.utils.permission import has_perm
from django.db.models import Sum
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
    filterset_fields = ["standard", "id", "number", "level", "risk_level", "is_concern"]
    search_fields = ["number", "content"]
    ordering = ["standard", "number_sort"]

    @transaction.atomic
    def perform_update(self, serializer):
        ins:StandardItem = self.get_object()
        old_full_score = ins.full_score
        newins: StandardItem = serializer.save()
        if old_full_score != newins.full_score:
            if newins.parent:
                newins.parent.full_score = StandardItem.objects.filter(parent=newins.parent).aggregate(Sum("full_score"))["full_score__sum"]
                newins.parent.save(update_fields=["full_score"])
                if newins.parent.parent:
                    newins.parent.parent.full_score = StandardItem.objects.filter(parent=newins.parent.parent).aggregate(Sum("full_score"))["full_score__sum"]
                    newins.parent.parent.save(update_fields=["full_score"])

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
    select_related_fields = ["company"]
    filterset_fields = ["company", "year", "standard", "standard__to_type", "state"]
    search_fields = ["company__name"]
    # data_filter = False
    # data_filter_field_user = "team_atask__member"
    
    def add_info_for_list(self, data):
        ids = [ins["id"] for ins in data]
        members_dict  = {}
        leaders_dict = {}
        members = AtaskTeam.objects.filter(atask__id__in=ids).order_by("duty_type").select_related('member', 'atask')
        for member in members:
            if member.atask.id not in members_dict:
                members_dict[member.atask.id] = []
            if member.duty_type == 10:
                leaders_dict[member.atask.id] = {"id": member.member.id, "name": member.member.name}
            members_dict[member.atask.id].append({
                "member_id": member.member.id,
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
            if task_id in leaders_dict:
                item["leader_id"] = leaders_dict[task_id]["id"]
                item["leader_name"] = leaders_dict[task_id]["name"]
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
        # if AtaskIssue.objects.filter(atask=self.get_object()).exists():
        #     raise ParseError("该任务下已存在审计数据,禁止删除")
        return super().destroy(request, *args, **kwargs)
    
    @action(methods=['put'], detail=True, perms_map={'put': "atask.update"})
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
    
    @action(methods=['post'], detail=True, perms_map={'post': "atask.update"}, serializer_class=serializers.Serializer)
    @transaction.atomic
    def send_mail(self, request, *args, **kwargs):
        """发送通知邮件"""
        notify_content = request.data.get("notify_content", None)
        ins:Atask = self.get_object()
        ins.notify_content = notify_content
        ins.save(update_fields=["notify_content"])
        sendMail(ins)
        return Response()
    
    @action(methods=['get'], detail=True, perms_map={'get': '*'},
            serializer_class=serializers.Serializer)
    def export_pptx(self, request, pk=None):
        """导出pptx"""
        ins:Atask = self.get_object()
        return Response({'path': export_pptx(ins, '安全审计总结', request.user)})
    
    @action(methods=['get'], detail=True, perms_map={'get': '*'})
    def export_docx(self, request, *args, **kwargs):
        """导出docx"""
        ins:Atask = self.get_object()
        type = request.query_params.get("type", 1)
        if type == "1" or type == 1:
            if self.request.user.is_superuser or has_perm(self.request.user, ["atask.udpate"]) or ins.leader == self.request.user:
                pass
            else:
                raise ParseError("仅组长可操作")
        return Response({'path': export_issue_docx(ins, type)})
    
    @action(methods=['post'], detail=True, perms_map={'post': 'atask.update'})
    def sync_standard(self, request, *args, **kwargs):
        ins:Atask = self.get_object()
        ins.init()
        return Response()
    
    @action(methods=['get'], detail=True, perms_map={'get': '*'})
    def export_report(self, request, *args, **kwargs):
        ins:Atask = self.get_object()
        if self.request.user.is_superuser or has_perm(self.request.user, ["atask.udpate"]) or ins.leader == request.user:
            pass
        else:
            raise ParseError("仅组长可操作")
        return Response({'path': export_atask_report(ins)})

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
    ordering = ["atask", "standarditem__number_sort"]

    def add_info_for_list(self, data):
        if isinstance(data, list):
            dataDict = {None: None}
            for item in data:
                dataDict[item["standarditem_"]["id"]] = item["id"]
                item["parent"] = dataDict.get(item["standarditem_"]["parent"], None)
        return data
    
    @transaction.atomic
    def perform_update(self, serializer):
        obj:AtaskItem = self.get_object()
        if self.request.user != obj.atask.leader:
            if self.request.user.is_superuser:
                pass
            else:
                raise ParseError("仅组长可操作")
        if obj.atask.state != Atask.S_DOING:
            raise ParseError("该任务状态下不可操作")
        ins:AtaskItem = serializer.save()
        # if ins.standarditem.is_concern and ins.is_suit is False:
        #     ins.score = 0
        #     ins.save()
        ins.cal_score(self.request.user)
        # ins.atask.cal()
        # ins.cal_score(self.request.user)
    
    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('atask', None):
            pass
        else:
            return self.queryset.none()
        return super().list(request, *args, **kwargs)
    
    @action(methods=['post'], detail=False, perms_map={'post': '*'}, serializer_class=serializers.Serializer)
    def related_ataskitem(self, request, *args, **kwargs):
        data = request.data
        standarditem = StandardItem.objects.get(id=data.get("standarditem"))
        concern_item = standarditem.related_concern_item()
        if concern_item:
            return Response(AtaskItemSerializer(AtaskItem.objects.get(atask=data["atask"], standarditem=concern_item)).data)
        raise ParseError("未找到最小扣分项")


class AtaskProblemViewSet(CustomModelViewSet):
    queryset = AtaskProblem.objects.all()
    serializer_class = AtaskProblemSerializer
    select_related_fields = ["atask", "create_by"]
    ordering_fields = ["atask", "create_time"]
    ordering = ["atask", "-create_time"]
    filterset_fields = ["atask"]

    def check_perm(self):
        ins:AtaskProblem = self.get_object()
        atask:Atask = ins.atask
        atask.check_do()
        if ins.create_by == self.request.user or self.request.user == atask.leader or has_perm(self.request.user, ["atask.create"]):
            pass
        else:
            raise ParseError("仅创建人/负责人可修改")

    def perform_update(self, serializer):
        self.check_perm()
        return super().perform_update(serializer)
    
    def perform_destroy(self, instance):
        self.check_perm()
        return super().perform_destroy(instance)


class AtaskIssueViewSet(CustomModelViewSet):
    queryset = AtaskIssue.objects.all()
    serializer_class = AtaskIssueSerializer
    select_related_fields = ["atask", "standarditem", "create_by", "atask__standard", "atask__company"]
    prefetch_related_fields = ["photos"]
    filterset_class = AtaskIssueFilter
    ordering_fields = ["atask", "standarditem__number_sort", "create_time"]
    ordering = ["atask", "standarditem__number_sort", "-create_time"]
    search_fields = ["content", "standarditem__number", "atask__company__name"]

    def add_info_for_list(self, data):
        if self.request.query_params.get("with_atask", "yes"):
            ataskIds = {}
            for item in data:
                ataskIds[item["atask"]] = {}
            atask_data = AtaskDetailSerializer(instance=Atask.objects.filter(id__in=ataskIds.keys()), many=True).data
            for item in atask_data:
                ataskIds[item["id"]] = item
            for item in data:
                item["atask_"] = ataskIds[item["atask"]]
        return data

    @transaction.atomic
    def perform_create(self, serializer):
        ins:AtaskIssue = serializer.save()
        AtaskIssue.cal_ataskitem_score(ins.atask, ins.create_by, ins.standarditem,None,ins.kill_score,None)
    
    @action(methods=['post'], detail=False, perms_map={'post': 'ataskissue.update'})
    @transaction.atomic
    def daoru(self, request, *args, **kwargs):
        path = request.data.get("path", "")
        ataskId = request.data.get("atask", "")
        create_by = request.user
        atask = Atask.objects.get(id=ataskId)
        if path:
            daoru_issue(settings.BASE_DIR + path, atask, create_by)
            return Response()
        raise ParseError("缺少path参数")
    
    def get_queryset(self):
        if self.request.method == 'GET':
            if  (self.request.query_params.get("atask", None) 
                or self.request.query_params.get("standitem", None)
                or self.request.query_params.get("standitem_belong", None)):
                pass
            elif has_perm(self.request.user, ["ataskissue.view"]):
                pass
            else:
                return self.queryset.none()
        return super().get_queryset()

    def check_perm(self):
        ins:AtaskIssue = self.get_object()
        atask:Atask = ins.atask
        atask.check_do()
        if ins.create_by == self.request.user or self.request.user == atask.leader or has_perm(self.request.user, ["atask.create"]):
            pass
        else:
            raise ParseError("仅创建人/负责人可修改")
        
    @transaction.atomic
    def perform_update(self, serializer):
        ins = self.get_object()
        old_kill_score, old_standarditem = ins.kill_score, ins.standarditem
        
        # 先检查权限
        self.check_perm()
        
        # 执行原始更新操作
        super().perform_update(serializer)
        
        # 刷新实例并执行后续操作
        ins = AtaskIssue.objects.get(id=ins.id)
        AtaskIssue.cal_ataskitem_score(
            ins.atask, 
            ins.update_by, 
            ins.standarditem, 
            old_standarditem, 
            ins.kill_score, 
            old_kill_score
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        self.check_perm()
        old_standarditem, atask, user = instance.standarditem, instance.atask, instance.create_by
        super().perform_destroy(instance)
        AtaskIssue.cal_ataskitem_score(atask, user, None, old_standarditem, None, None)
    
    @action(methods=['get'], detail=False, perms_map={'get': '*'},
            serializer_class=serializers.Serializer)
    def export_excel(self, request, pk=None):
        """导出excel
        导出excel
        """
        with_photos = request.query_params.get("with_photos", "no") == "yes"
        field_data = ['一级要素', '条款号', '问题描述', '风险等级', '扣分分值', '检查人', '创建时间']
        if with_photos:
            field_data.insert(0, "采用标准")
            field_data.insert(0, "审计对象")
            field_data.append('图片1')
            field_data.append('图片2')
        queryset = self.filter_queryset(self.get_queryset())
        if queryset.count() > 300:
            raise ParseError('数据量超过300,请筛选后导出')

        if with_photos:
            odata = AtaskIssueExportWithImgSerializer(queryset, many=True).data
        else:
            odata = AtaskIssueExportSerializer(queryset, many=True).data
        # 处理数据
        data = []
        for i in odata:
            if with_photos:
                photos = i.get("photos_", [])
                photo1 = photos[0]["path"] if len(photos) > 0 else None
                photo2 = photos[1]["path"] if len(photos) > 1 else None
                data.append(
                    [i['atask_company_name'],
                     i['atask_standard_name'],
                     i['level_10_name'],
                    i.get('standarditem_number', None),
                    i['content'],
                    R_LEVEL_DICT.get(i["risk_level"], None),
                    i["kill_score"],
                    i["create_by_name"], i["create_time"],
                    photo1, photo2]
                )
            else:
                data.append(
                    [i['level_10_name'],
                    i.get('standarditem_number', None),
                    i['content'],
                    R_LEVEL_DICT.get(i["risk_level"], None),
                    i["kill_score"],
                    i["create_by_name"], i["create_time"]]
                )
        if with_photos:
            path = export_excel(field_data, data, '问题清单', img_field_index=[9, 10])
        else:
            path = export_excel(field_data, data, '问题清单')
        return Response({'path': path})