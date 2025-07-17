from apps.utils.serializers import CustomModelSerializer
from apps.audit.models import (Standard, StandardItem, 
                               Company, Atask, C_COMPANY, AtaskTeam,
                               AtaskItem, AtaskIssue, AtaskProblem)
from rest_framework.exceptions import ParseError
from rest_framework import serializers
from django.db import transaction
from apps.system.models import User
from apps.utils.constants import EXCLUDE_FIELDS, EXCLUDE_FIELDS_BASE
from apps.system.serializers import FileSerializer

class StandardSerializer(CustomModelSerializer):
    class Meta:
        model = Standard
        fields = "__all__"


class StandardItemSerializer(CustomModelSerializer):
    class Meta:
        model = StandardItem
        fields = "__all__"


class CompanySerializer(CustomModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"

class AtaskSerializer(CustomModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_ = CompanySerializer(source="company", read_only=True)
    standard_name = serializers.CharField(source="standard.name", read_only=True)
    standard_to_type = serializers.CharField(source="standard.to_type", read_only=True)
    class Meta:
        model = Atask
        fields = "__all__"
        read_only_fields = ["enabled"]
    
    def validate(self, attrs):
        company:Company = attrs["company"]
        if company.level != C_COMPANY:
            raise ParseError("只可选择公司")
        standard:Standard = attrs["standard"]
        if standard.to_type not in company.types:
            raise ParseError("该公司不适用该标准")
        return attrs
    
    def update(self, instance, validated_data):
        atask:Atask = instance
        if atask.state != Atask.S_WAIT:
            raise ParseError("该审计任务非待开始状态无法修改")
        return super().update(instance, validated_data)

class AtaskTeamSerializer(CustomModelSerializer):
    member_name = serializers.CharField(source="member.name", read_only=True)
    member_gender = serializers.CharField(source="member.gender", read_only=True)
    member_phone = serializers.CharField(source="member.phone", read_only=True)
    class Meta:
        model = AtaskTeam
        fields = "__all__"

    def create(self, validated_data):
        atask:Atask = validated_data["atask"]
        member:User = validated_data["member"]
        if AtaskTeam.objects.filter(atask=atask, member=member).exists():
            raise ParseError("该成员已添加")
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("member")
        duty_type = validated_data["duty_type"]
        if duty_type == 10 and AtaskTeam.objects.filter(atask=instance.atask, duty_type=10).exclude(pk=instance.pk).exists():
            raise ParseError("组长已存在")
        return super().update(instance, validated_data)

class AtaskDetailSerializer(AtaskSerializer):
    team = AtaskTeamSerializer(many=True, read_only=True)
    
class AtaskItemSerializer(CustomModelSerializer):
    check_user_name = serializers.CharField(source="check_user.name", read_only=True)
    standarditem_ = StandardItemSerializer(source="standarditem", read_only=True)
    class Meta:
        model = AtaskItem
        fields = "__all__"

class AtaskItemCheckSerializer(CustomModelSerializer):
    # cur_kill = serializers.IntegerField(write_only=True)
    class Meta:
        model = AtaskItem
        fields = ["id", "is_suit", "note"]
        # extra_kwars = {
        #     "socre": {"read_only": True},
        #     "kill_score": {"read_only": True}
        # }
    def to_representation(self, instance):
        return AtaskItemSerializer(instance).data
    
    # def update(self, instance, validated_data):
    #     ataskitem:AtaskItem = instance
    #     cur_kil:int = validated_data.pop("cur_kill")
    #     kill_score:int = ataskitem.kill_score + cur_kil
    #     if kill_score > ataskitem.standarditem.full_score:
    #         raise ParseError("扣分不能大于总分")
    #     validated_data["kill_score"] = kill_score
    #     return super().update(instance, validated_data)

class AtaskIssueSerializer(CustomModelSerializer):
    standard = serializers.CharField(source="atask.standard.id", read_only=True)
    standarditem_number = serializers.CharField(source="standarditem.number", read_only=True)
    standarditem_level = serializers.CharField(source="standarditem.level", read_only=True)
    standarditem_parent = serializers.CharField(source="standarditem.parent.id", read_only=True)
    standarditem_standard = serializers.CharField(source="standarditem.standard", read_only=True)
    create_by_name = serializers.CharField(source="create_by.name", read_only=True)
    photos_ = FileSerializer(many=True, read_only=True, source="photos")
    class Meta:
        model = AtaskIssue
        fields = "__all__"
        read_only_fields = EXCLUDE_FIELDS_BASE
        extra_kwars = {
            "atask": {"required": True}
        }

    def validate(self, attrs):
        if "atask" not in attrs or attrs["atask"] is None:
            raise ParseError("未找到审计任务")
        risk_level = attrs.get("risk_level", None)
        if risk_level is None:
            standarditem:StandardItem = attrs.get("standarditem", None)
            if standarditem is not None:
                attrs["risk_level"] = standarditem.risk_level
        return super().validate(attrs)
    
    # def create(self, validated_data):
    #     if "ataskitem" in validated_data:
    #         pass
    #     elif "atask" in validated_data and "standarditem" in validated_data:
    #         try:
    #             ataskitem:AtaskItem = AtaskItem.objects.get(atask__id=validated_data["atask"], standarditem__id=validated_data["standarditem"])
    #         except Exception:
    #             raise ParseError("未找到对应审计项")
    #         validated_data["ataskitem"] = ataskitem
    #         validated_data.pop("atask")
    #         validated_data.pop("standarditem")
    #     ataskitem:AtaskItem = validated_data["ataskitem"]
    #     ataskitem.atask.check_do()
    #     return super().create(validated_data)
    
class AtaskIssueExportSerializer(CustomModelSerializer):
    standarditem_number = serializers.CharField(source="standarditem.number", read_only=True)
    create_by_name = serializers.CharField(source="create_by.name", read_only=True)
    risk_level_display = serializers.SerializerMethodField()
    level_10_name = serializers.SerializerMethodField()
    class Meta:
        model = AtaskIssue
        fields = "__all__"
    
    def get_risk_level_display(self, obj):
        if obj.standarditem:  # 检查外键是否存在
            return obj.standarditem.get_risk_level_display()
        return None

    def get_level_10_name(self, obj):
        standitem = obj.standarditem
        if standitem:
            p_stand:StandardItem = standitem.parent
            if p_stand.level == StandardItem.L_1:
                return p_stand.content
            elif p_stand.level == StandardItem.L_2:
                return p_stand.parent.content


class AtaskProblemSerializer(CustomModelSerializer):
    create_by_name = serializers.CharField(source="create_by.name", read_only=True)
    class Meta:
        model = AtaskProblem
        fields = "__all__"
        read_only_fields = EXCLUDE_FIELDS
    