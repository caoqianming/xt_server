from apps.utils.models import CommonADModel, BaseModel
from apps.system.models import User, File
from django.db import models
from rest_framework.exceptions import ParseError
from django.db.models import Sum

T_KS = 10
T_SN = 20
T_SH = 30
TYS = (
    (T_KS, "矿山"),
    (T_SN, "水泥"),
    (T_SH, "商混")
)
TKS_DICT = {
    T_KS: "矿山",
    T_SN: "水泥",
    T_SH: "商混"
}
C_GROUP = 10
C_AREA = 20
C_COMPANY = 30
# Create your models here.
class Standard(CommonADModel):
    name = models.CharField('标准名称', max_length=100, unique=True)
    to_type = models.PositiveSmallIntegerField("适用类型", default=T_KS, choices=TYS)
    enabled = models.BooleanField("启用", default=False)
    total_score = models.PositiveIntegerField("总分", default=0)

    class Meta:
        verbose_name = verbose_name_plural = '审计标准'

    def __str__(self):
        return self.name

class StandardItem(BaseModel):
    L_1 = 10
    L_2 = 20
    L_3 = 30
    R_LOW = 10
    R_MID = 20
    R_HIGH = 30
    R_VH = 40
    standard = models.ForeignKey(Standard, verbose_name="关联审计标准", on_delete=models.CASCADE)
    # cate = models.PositiveSmallIntegerField("大类", choices=((10, "基础部分"), (20, "现场部分")))
    number = models.CharField('条款号', max_length=100)
    number_sort = models.CharField('排序号', null=True, blank=True)
    level = models.PositiveSmallIntegerField("条款等级", 
                default=L_1, choices=((L_1, "一级"), (L_2, "二级"), (L_3, "三级")), null=True, blank=True)
    risk_level = models.PositiveSmallIntegerField("风险等级", 
                choices=((R_LOW, "低风险"), (R_MID, "中风险"), (R_HIGH, "高风险"), (R_VH, "重大风险")),
                null=True, blank=True)
    is_concern = models.BooleanField("是否最小扣分项", default=False)
    content = models.TextField('条款内容', null=True, blank=True)
    method = models.TextField('考评办法', null=True, blank=True)
    full_score = models.PositiveSmallIntegerField("满分分值", null=True, blank=True)
    parent = models.ForeignKey('self', verbose_name="上级条款", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计标准条款'

    def related_concern_item(self):
        if self.is_concern:
            return self
        else:
            obj = self.parent
            if obj.is_concern:
                return obj
            return None

class Company(CommonADModel):
    name = models.CharField('名称', max_length=100)
    level = models.PositiveSmallIntegerField("公司级别", choices=((C_GROUP, "集团"), (C_AREA, "区域"), (C_COMPANY, "公司")))
    parent = models.ForeignKey('self', verbose_name="上级", on_delete=models.CASCADE, null=True, blank=True)
    types = models.JSONField('类型', default=list, blank=True, null=True)
    email = models.EmailField('联系邮箱', null=True, blank=True)
    address = models.CharField('地址', max_length=100, null=True, blank=True)
    contact = models.CharField('联系人', max_length=100, null=True, blank=True)
    phone = models.CharField('联系电话', max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '受审计单位'

    def __str__(self):
        return self.name

class Atask(CommonADModel):
    S_WAIT = 10
    S_DOING = 20
    S_DONE = 30
    year = models.PositiveIntegerField('审计年度')
    state = models.PositiveSmallIntegerField("状态", 
            choices=((S_WAIT, "待开始"), (S_DOING, "进行中"), (S_DONE, "已完成")), default=S_WAIT)
    company = models.ForeignKey(Company, verbose_name="审计对象", on_delete=models.CASCADE)
    start_date = models.DateField('开始日期', null=True, blank=True)
    end_date = models.DateField('结束日期', null=True, blank=True)
    standard = models.ForeignKey(Standard, verbose_name="审计标准", on_delete=models.CASCADE)
    notify_content = models.TextField('通知内容', null=True, blank=True)
    note = models.TextField('备注', null=True, blank=True)
    score = models.PositiveIntegerField("得分", null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计任务'

    @property
    def leader(self):
        ateam = AtaskTeam.objects.filter(atask=self, duty_type=10).first()
        if ateam:
            return ateam.member
        return None
    
    @property
    def team(self):
        return AtaskTeam.objects.filter(atask=self).order_by("duty_type")
    
    def check_do(self):
        if self.state != Atask.S_DOING:
            raise ParseError("该任务状态下不可操作")
        
    def init(self):
        for st in StandardItem.objects.filter(standard=self.standard).order_by("number"):
            checked = None
            is_suit = None
            kill_score = None
            if st.is_concern:
                checked = False
                is_suit = True
                kill_score = 0
            AtaskItem.objects.get_or_create(atask=self, standarditem=st, defaults={"checked": checked, 
                                                                                  "is_suit": is_suit, "kill_score": kill_score, "score": st.full_score})

class AtaskTeam(BaseModel):
    atask = models.ForeignKey(Atask, verbose_name="关联审计任务", on_delete=models.CASCADE, related_name="team_atask")
    member = models.ForeignKey(User, verbose_name="成员", on_delete=models.CASCADE)
    duty_type = models.PositiveSmallIntegerField("职责类型", choices=((10, "组长"), (20, "组员")))

    class Meta:
        verbose_name = verbose_name_plural = '审计任务组'


class AtaskItem(BaseModel):
    atask = models.ForeignKey(Atask, verbose_name="关联审计任务", on_delete=models.CASCADE)
    standarditem = models.ForeignKey(StandardItem, verbose_name="关联审计标准条款", on_delete=models.CASCADE)
    is_suit = models.BooleanField("是否适用", null=True, blank=True)
    checked = models.BooleanField("是否已检查", null=True, blank=True)
    check_user = models.ForeignKey(User, verbose_name="检查人", on_delete=models.CASCADE, null=True, blank=True)
    note = models.TextField('备注', null=True, blank=True)
    kill_score = models.PositiveSmallIntegerField("扣分", null=True, blank=True)
    score = models.PositiveSmallIntegerField("得分", null=True, blank=True)
    
    class Meta:
        verbose_name = verbose_name_plural = '审计条款'

    def cal_score(self, user):
        ataskitem_qs = AtaskItem.objects.filter(atask=self.atask)
        if self.standarditem.is_concern:
            if self.is_suit is False:
                raise ParseError("所属扣分项不适用")
            self.score = self.standarditem.full_score - self.kill_score
            if self.score < 0:
                raise ParseError(f"满分为{self.standarditem.full_score}, 扣分已超出")
            self.checked = True
            self.check_user = user if self.check_user is None else self.check_user
            self.save()
            if self.standarditem.level == 30:
                l_20 = ataskitem_qs.get(standarditem=self.standarditem.parent)
                l_20.kill_score = ataskitem_qs.filter(standarditem__parent=self.standarditem.parent).aggregate(Sum('kill_score'))['kill_score__sum']
                l_20.score = ataskitem_qs.filter(standarditem__parent=self.standarditem.parent).aggregate(Sum('score'))['score__sum']
                l_20.checked = True
                l_20.save(update_fields=["kill_score", "score", "checked"])
                l_10 = ataskitem_qs.get(standarditem=l_20.standarditem.parent)
            elif self.standarditem.level == 20:
                l_10 = ataskitem_qs.get(standarditem=self.standarditem.parent)
            l_10.kill_score = ataskitem_qs.filter(standarditem__parent=l_10.standarditem).aggregate(Sum('kill_score'))['kill_score__sum']
            l_10.score = ataskitem_qs.filter(standarditem__parent=l_10.standarditem).aggregate(Sum('score'))['score__sum']
            l_10.checked = True
            l_10.save(update_fields=["kill_score", "score", "checked"])
            self.atask.score = ataskitem_qs.filter(standarditem__is_concern=True).aggregate(Sum('score'))['score__sum']
            self.atask.save(update_fields=["score"])
        else:
            self.checked = True
            self.check_user = user if self.check_user is None else self.check_user
            self.save()
            standarditem_p:StandardItem = self.standarditem.parent
            if standarditem_p.is_concern:
                ataskitem = ataskitem_qs.get(standarditem=standarditem_p)
                ataskitem.kill_score = ataskitem_qs.filter(standarditem__parent=standarditem_p).aggregate(Sum('kill_score'))['kill_score__sum'] or 0
                ataskitem.save(update_fields=["kill_score"])
                return ataskitem.cal_score(user)
            else:
                raise ParseError("找不到上级审计条款")
        

class AtaskIssue(CommonADModel):
    """
    create_by即为检查人
    """
    atask = models.ForeignKey(Atask, verbose_name="关联审计任务", on_delete=models.CASCADE, null=True, blank=True)
    standarditem = models.ForeignKey(StandardItem, verbose_name="关联审计标准条款", on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField('问题内容', null=True, blank=True)
    photos = models.ManyToManyField(File, verbose_name="问题照片", blank=True)
    note = models.TextField('备注', null=True, blank=True)
    kill_score = models.PositiveSmallIntegerField("扣分", null=True, blank=True)
    number = models.TextField("问题编号", null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '审计问题'

    @classmethod
    def cal(cls, atask:Atask, user:User, standarditem:StandardItem):
        try:
            ataskitem = AtaskItem.objects.get(atask=atask, standarditem=standarditem)
        except Exception as e:
            raise ParseError(f"找不到该审计条款-{str(e)}")
        kill_score_all = AtaskIssue.objects.filter(atask=atask, standarditem=standarditem).aggregate(Sum('kill_score'))['kill_score__sum'] or 0
        ataskitem.kill_score = kill_score_all
        ataskitem.save(update_fields=["kill_score"])
        ataskitem.cal_score(user)

    @classmethod
    def cal_ataskitem_score(cls, atask:Atask, user:User, 
                            new_standarditem:StandardItem=None, 
                            old_standarditem:StandardItem=None,
                            new_kill_score=None, old_kill_score=None):
        if new_kill_score == old_kill_score and old_standarditem == new_standarditem:
            # 此时不用处理
            pass
        elif new_standarditem is not None and old_standarditem is not None and new_standarditem == old_standarditem:
            cls.cal(atask, user, new_standarditem)
        elif new_standarditem is not None:
            cls.cal(atask, user, new_standarditem)
        elif old_standarditem is not None:
            cls.cal(atask, user, old_standarditem)
            
