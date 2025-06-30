from pptx import Presentation
from pptx.util import Inches
from server.settings import BASE_DIR
from apps.audit.models import Atask, AtaskIssue
import os
from datetime import datetime

templ = os.path.join(BASE_DIR, "media/muban/安全审计总结.pptx")

def export_pptx(atask:Atask, FileName:str):
    prs = Presentation(templ)
    new_prs = Presentation()
    for i, slide in enumerate(prs.slides):
        # 复制原幻灯片到新PPT（保持原布局）
        new_slide = new_prs.slides.add_slide(slide.slide_layout)
        for shape in slide.shapes:
                if shape.has_text_frame:
                    new_shape = new_slide.shapes.add_textbox(
                        shape.left, shape.top, shape.width, shape.height
                    )
                    new_shape.text_frame.text = shape.text_frame.text
    # title_only_slide_layout = prs.slide_layouts[3]
    # slide = prs.slides.add_slide(title_only_slide_layout)
    # shapes = slide.shapes
    
    # rows = cols = 2
    # left = top = Inches(2.0)
    # width = Inches(6.0)
    # height = Inches(0.8)

    # table = shapes.add_table(rows, cols, left, top, width, height).table

    # # set column widths
    # table.columns[0].width = Inches(2.0)
    # table.columns[1].width = Inches(4.0)

    # # write column headings
    # table.cell(0, 0).text = 'Foo'
    # table.cell(0, 1).text = 'Bar'

    # # write body cells
    # table.cell(1, 0).text = 'Baz'
    # table.cell(1, 1).text = 'Qux'

    path = f"media/temp/{FileName}_{atask.id}.pptx"
    new_prs.save(os.path.join(BASE_DIR, path))
    return path