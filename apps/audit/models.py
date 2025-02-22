from apps.utils.models import CommonADModel, BaseModel
from django.db import models

T_KS = 10
T_SN = 20
T_SH = 30
TYS = (
    (T_KS, "矿山"),
    (T_SN, "水泥"),
    (T_SH, "商混")
)
COM_GROUP = 10
COM_AREA = 20
COM_DEPT = 30
# Create your models here.
class Standard(CommonADModel):
    name = models.CharField('标准名称', max_length=100, unique=True)
    to_type = models.PositiveSmallIntegerField("适用类型", default=T_KS, choices=TYS)

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
    score = models.PositiveSmallIntegerField("满分分值")

    class Meta:
        verbose_name = verbose_name_plural = '审计标准条款'


class Company(CommonADModel):
    name = models.CharField('名称', max_length=100)
    level = models.PositiveSmallIntegerField("公司级别", choices=((COM_GROUP, "集团"), (COM_AREA, "区域"), (COM_DEPT, "公司")))
    parent = models.ForeignKey('self', verbose_name="上级", on_delete=models.CASCADE, null=True, blank=True)
    types = models.JSONField('类型', default=list, blank=True, null=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计单位'
