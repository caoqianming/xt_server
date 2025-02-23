from apps.utils.models import CommonADModel, BaseModel
from apps.system.models import User, File
from django.db import models

T_KS = 10
T_SN = 20
T_SH = 30
TYS = (
    (T_KS, "矿山"),
    (T_SN, "水泥"),
    (T_SH, "商混")
)
C_GROUP = 10
C_AREA = 20
C_COMPANY = 30
# Create your models here.
class Standard(CommonADModel):
    name = models.CharField('标准名称', max_length=100, unique=True)
    to_type = models.PositiveSmallIntegerField("适用类型", default=T_KS, choices=TYS)
    enabled = models.BooleanField("启用", default=False)

    class Meta:
        verbose_name = verbose_name_plural = '审计标准'


class StandardItem(BaseModel):
    L_1 = 10
    L_2 = 20
    L_3 = 30
    R_LOW = 10
    R_MID = 20
    R_HIGH = 30
    R_VH = 40
    standard = models.ForeignKey(Standard, verbose_name="关联审计标准", on_delete=models.CASCADE)
    number = models.CharField('条款号', max_length=100)
    level = models.PositiveSmallIntegerField("条款等级", default=L_1, choices=((L_1, "一级"), (L_2, "二级"), (L_3, "三级")))
    risk_level = models.PositiveSmallIntegerField("风险等级", default=R_LOW, choices=((R_LOW, "低风险"), (R_MID, "中风险"), (R_HIGH, "高风险"), (R_VH, "重大风险")))
    content = models.TextField('条款内容')
    method = models.TextField('考评办法')
    full_score = models.PositiveSmallIntegerField("满分分值")

    class Meta:
        verbose_name = verbose_name_plural = '审计标准条款'


class Company(CommonADModel):
    name = models.CharField('名称', max_length=100)
    level = models.PositiveSmallIntegerField("公司级别", choices=((C_GROUP, "集团"), (C_AREA, "区域"), (C_COMPANY, "公司")))
    parent = models.ForeignKey('self', verbose_name="上级", on_delete=models.CASCADE, null=True, blank=True)
    types = models.JSONField('类型', default=list, blank=True, null=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计单位'

class Atask(CommonADModel):
    year = models.PositiveIntegerField('审计年度')
    company = models.ForeignKey(Company, verbose_name="审计对象", on_delete=models.CASCADE)
    standard = models.ForeignKey(Standard, verbose_name="审计标准", on_delete=models.CASCADE)
    enabled = models.BooleanField("启用", default=False)
    note = models.TextField('备注', null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计任务'

    @property
    def leader(self):
        ateam = AtaskTeam = AtaskTeam.objects.filter(atask=self, duty_type=10).first()
        if ateam:
            return ateam.member
        return None

class AtaskTeam(BaseModel):
    atask = models.ForeignKey(Atask, verbose_name="关联审计任务", on_delete=models.CASCADE)
    member = models.ForeignKey(User, verbose_name="成员", on_delete=models.CASCADE)
    duty_type = models.PositiveSmallIntegerField("职责类型", choices=((10, "组长"), (20, "组员")))

    class Meta:
        verbose_name = verbose_name_plural = '审计任务组'


class AtaskItem(BaseModel):
    atask = models.ForeignKey(Atask, verbose_name="关联审计任务", on_delete=models.CASCADE)
    standard_item = models.ForeignKey(StandardItem, verbose_name="关联审计标准条款", on_delete=models.CASCADE)
    is_suit = models.BooleanField("是否适用", default=True)
    checked = models.BooleanField("是否已检查", default=False)
    note = models.TextField('备注', null=True, blank=True)
    kill_score = models.PositiveSmallIntegerField("扣分", default=0)
    score = models.PositiveSmallIntegerField("得分", null=True, blank=True)
    
    class Meta:
        verbose_name = verbose_name_plural = '审计条款'

class AtaskIssue(CommonADModel):
    """
    create_by即为检查人
    """
    atask_item = models.ForeignKey(AtaskItem, verbose_name="关联审计条款", on_delete=models.CASCADE)
    content = models.TextField('问题内容')
    photos = models.ManyToManyField(File, verbose_name="问题照片", blank=True)
    note = models.TextField('备注', null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计问题'