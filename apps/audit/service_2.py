from server.settings import BASE_DIR
from apps.audit.models import Atask, AtaskItem, AtaskIssue, AtaskProblem
from openpyxl import load_workbook
import os
from apps.audit.models import R_LEVEL_DICT
from docxtpl import DocxTemplate

templ = os.path.join(BASE_DIR, "media/muban/xxxx任务问题清单.xlsx")
def export_issue_excel(atask:Atask):
    wb = load_workbook(filename=templ)
    ws = wb.active
    ws["A1"] = f'{atask.company.name}安全审计问题清单'
    ws["C2"] = f"{atask.company.audit_scope}"
    member_name_list = list(atask.team.values_list("member__name", flat=True))
    ws["C3"] = ','.join(member_name_list)
    kfx_qs = AtaskItem.objects.filter(atask=atask, is_suit=False).values("standarditem__number", "standarditem__full_score")
    kfx_number_list = [kfx["standarditem__number"] for kfx in kfx_qs]
    kfx_full_score_list = [kfx["standarditem__full_score"] for kfx in kfx_qs]
    kfx_str = '/'.join(kfx_number_list)
    kfx_score_str = '+'.join([str(score) for score in kfx_full_score_list])
    ws["C4"] = f'{kfx_str}={kfx_score_str}={sum(kfx_full_score_list)}'
    count = AtaskIssue.objects.filter(atask=atask).count()
    ws.move_range("A9:F12", rows=count)
    # ws.insert_rows(6, count)
    # kill_score_all = 0
    # for ind, item in enumerate(AtaskIssue.objects.filter(atask=atask)):
    #     row = 6+ind
    #     standarditem = item.standarditem
    #     if standarditem:
    #         if standarditem.level == 10:
    #             ws[f"A{row}"] = standarditem.content
    #         elif standarditem.level == 20:
    #             ws[f"A{row}"] = standarditem.parent.content
    #         elif standarditem.level == 30:
    #             ws[f"A{row}"] = standarditem.parent.parent.content
    #     ws[f"B{row}"] = standarditem.number if standarditem else ""
    #     ws[f"C{row}"] = item.content
    #     ws[f"D{row}"] = R_LEVEL_DICT.get(item.risk_level, "")
    #     ws[f"E{row}"] = item.kill_score if item.kill_score else ""
    #     if item.kill_score is not None:
    #         kill_score_all += item.kill_score
    #     ws[f"F{row}"] = item.create_by.name
    path = f'/media/temp/任务问题清单_{atask.id}.xlsx'
    wb.save(BASE_DIR + path)
    return path



templ2 = os.path.join(BASE_DIR, "media/muban/xxx任务问题清单.docx")
def export_issue_docx(atask:Atask):
    doc = DocxTemplate(templ2)
    title = f'{atask.company.name}安全审计问题清单'
    audit_scope = atask.company.audit_scope if atask.company.audit_scope else ""
    member_name_list = list(atask.team.values_list("member__name", flat=True))
    member_names = ','.join(member_name_list)
    kfx_qs = AtaskItem.objects.filter(atask=atask, is_suit=False).values("standarditem__number", "standarditem__full_score")
    kfx_number_list = [kfx["standarditem__number"] for kfx in kfx_qs]
    kfx_full_score_list = [kfx["standarditem__full_score"] for kfx in kfx_qs]
    kfx_str = '/'.join(kfx_number_list)
    kfx_score_str = '+'.join([str(score) for score in kfx_full_score_list])
    sum_kfx_score = sum(kfx_full_score_list)
    if sum_kfx_score == 0:
        kfx = '无'
    else:
        kfx = f'{kfx_str}={kfx_score_str}={sum_kfx_score}'
    issues = []
    kill_score_all = 0
    for item in AtaskIssue.objects.filter(atask=atask).order_by("atask", "standarditem__number_sort", "-create_time"):
        standarditem = item.standarditem
        if standarditem:
            if standarditem.level == 10:
                content = standarditem.content
            elif standarditem.level == 20:
                content = standarditem.parent.content
            elif standarditem.level == 30:
                content = standarditem.parent.parent.content
        else:
            content = ""
        issues.append({
            "c": content,
            "n": standarditem.number if standarditem else "",
            "issue_content": item.content,
            "r": R_LEVEL_DICT.get(item.risk_level, ""),
            "k": item.kill_score if item.kill_score is not None else "",
            "x": item.create_by.name,
        })
        if item.kill_score is not None:
            kill_score_all += item.kill_score
        
    problems = []
    for ind, item in enumerate(AtaskProblem.objects.filter(atask=atask).order_by("atask", "-create_time")):
        problems.append({
            "index": ind+1,
            "content": item.content,
        })
    context = {
        "title": title,
        "audit_scope": audit_scope,
        "member_names": member_names,
        "kfx": kfx,
        "issues": issues,
        "problems": problems,
        "s": kill_score_all
    }
    doc.render(context)
    path = f'/media/temp/任务问题清单_{atask.id}.docx'
    doc.save(BASE_DIR + path)
    return path