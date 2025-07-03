from pptx import Presentation
from pptx.util import Inches
from server.settings import BASE_DIR
from apps.audit.models import Atask, AtaskIssue
import os
from datetime import datetime
from pptx.util import Pt
from PIL import Image

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
        photos = issue.photos

        left = top = Inches(1.8)
        if photos.exists():
            top = Inches(1.2)
        slide = prs.slides.add_slide(prs.slide_layouts[2])
        
        # 3. 将新幻灯片移动到指定位置
        target_position = ind + 5
        slides = prs.slides._sldIdLst  # 获取幻灯片列表
        slides.insert(target_position, slides[-1])  # 将最后一张插入到目标位置

        shapes = slide.shapes

        rows = cols = 2
        width = Inches(10.0)
        height = Inches(1.2)

        table = shapes.add_table(rows, cols, left, top, width, height).table

        # set column widths
        table.columns[0].width = Inches(2.0)
        table.columns[1].width = Inches(8.0)

        # write column headings
        table.cell(0, 0).text = '条款'
        table.cell(0, 1).text = '问题描述'

        # write body cells
        table.cell(1, 0).text = f'{issue.standarditem.number} {issue.standarditem.parent.parent.content}'  if issue.standarditem else ""
        table.cell(1, 1).text = issue.content

        # 设置不同的标题和内容字体大小
        for row in range(rows):
            for col in range(cols):
                tf = table.cell(row, col).text_frame
                for paragraph in tf.paragraphs:
                    for run in paragraph.runs:
                        if row == 0:  # 标题行
                            run.font.size = Pt(18)  # 标题字体大小
                            run.font.bold = True    # 标题加粗
                        else:         # 内容行
                            run.font.size = Pt(20)  # 内容字体大小

        if photos.exists():
            num_images = min(photos.count(), 3)  # 不超过3张
            img_height = Inches(4)  # 固定高度
            min_width = Inches(2.4) 
            spacing = Inches(0.2)     # 图片间隔
            top_position = Inches(2.8)  # 图片起始Y位置

            # 计算所有图片的自适应宽度
            img_widths = []
            for v in photos.all()[:3]:
                img_path = BASE_DIR + v.path
                with Image.open(img_path) as img:
                    width_px, height_px = img.size
                    aspect_ratio = width_px / height_px  # 宽高比（宽度/高度）h)
                    width = max(img_height * aspect_ratio, min_width)
                    img_widths.append(width)

            # 计算总宽度和起始位置（居中）
            total_width = sum(img_widths) + (num_images - 1) * spacing
            start_left = (Inches(10) - total_width) / 2 + Inches(2)  # 居中

            # 添加图片
            current_left = start_left
            for i, v in enumerate(photos.all()[:3]):
                img_path = BASE_DIR + v.path
                slide.shapes.add_picture(
                    img_path,
                    current_left, top_position,
                    height=img_height,
                    width=img_widths[i]
                )
                current_left += img_widths[i] + spacing  # 移动到下一张图片位置

    path = f"media/temp/{FileName}_{atask.id}.pptx"
    prs.save(os.path.join(BASE_DIR, path))
    return path