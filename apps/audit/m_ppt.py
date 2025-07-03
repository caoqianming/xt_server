from pptx import Presentation
from pptx.util import Inches
from server.settings import BASE_DIR
from apps.audit.models import Atask, AtaskIssue
import os
from datetime import datetime

templ = os.path.join(BASE_DIR, "media/muban/安全审计总结.pptx")

def export_pptx(atask:Atask, FileName:str):
   
    def replace_text_preserve_formatting(shape, old_text, new_text):
        if not shape.has_text_frame:
            return False
        
        text_frame = shape.text_frame
        found = False
        
        for paragraph in text_frame.paragraphs:
            for run in paragraph.runs:
                if old_text in run.text:
                    # 替换文本但保留run的格式
                    run.text = run.text.replace(old_text, new_text)
                    found = True
        
        return found
    prs = Presentation(templ)

    slide = prs.slides[0]
    for shape in slide.shapes:
        if shape.has_text_frame:
            if shape.text == "company_name":
                replace_text_preserve_formatting(shape, "company_name", atask.company.name)
            elif shape.text == "date":
                replace_text_preserve_formatting(shape, "date", datetime.now().strftime("%Y-%m-%d"))
            elif shape.text == "leader":
                replace_text_preserve_formatting(shape, "leader", atask.leader.name)

    issues = AtaskIssue.objects.filter(atask=atask).order_by("atask", "standarditem__number_sort", "-create_time")
    for ind, issue in enumerate(issues):
        slide = prs.slides.add_slide(prs.slide_layouts[2])
        
        # 3. 将新幻灯片移动到指定位置
        # target_position = ind + 5
        # slides = prs.slides._sldIdLst  # 获取幻灯片列表
        # slides.insert(target_position, slides[-1])  # 将最后一张插入到目标位置
        # del slides[-1]  # 删除原位置的重复引用

        shapes = slide.shapes

        rows = cols = 2
        left = top = Inches(2.0)
        width = Inches(10.0)
        height = Inches(0.8)

        table = shapes.add_table(rows, cols, left, top, width, height).table

        # set column widths
        table.columns[0].width = Inches(2.0)
        table.columns[1].width = Inches(8.0)

        # write column headings
        table.cell(0, 0).text = '条款'
        table.cell(0, 1).text = '问题描述'

        # write body cells
        table.cell(1, 0).text = issue.standarditem.number if issue.standarditem else ""
        table.cell(1, 1).text = issue.content

    path = f"media/temp/{FileName}_{atask.id}.pptx"
    prs.save(os.path.join(BASE_DIR, path))
    return path