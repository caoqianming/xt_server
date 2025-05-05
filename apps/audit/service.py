from apps.audit.models import Standard, StandardItem
from openpyxl import load_workbook

def daoru_standard(path: str, sta: Standard):
    wb = load_workbook(path)
    sheets = wb.sheetnames
    current_item1 = None
    current_item2 = None
    for sheet in sheets:
        if "基础" in sheet or "现场" in sheet:
            ws = wb[sheet]
            cate = 10 if "基础" in sheet else 20
            i = 3
            while ws[f'f{i}'].value:
                number1 = ws[f'a{i}'].value
                content1 = ws[f'b{i}'].value
                number2 = ws[f'c{i}'].value
                content2 = ws[f'd{i}'].value
                level_str = ws[f'e{i}'].value.strip() if ws[f'e{i}'].value else None
                level = 10 if level_str == "★" else 20 if level_str == "★★" else 30 if level_str == "★★★" else 40 if level_str == "★★★★" else None
                number3 = ws[f'f{i}'].value
                content3 = ws[f'g{i}'].value
                method = ws[f'h{i}'].value
                full_score = int(ws[f'i{i}'].value)
                if number1:
                    current_item1, _ = StandardItem.objects.get_or_create(
                        number = number1,
                        standard = sta,
                        cate = cate,
                        defaults={
                            "content": content1
                        }
                    )
                if number2:
                    current_item2, _ = StandardItem.objects.get_or_create(
                        number = number2,
                        standard = sta,
                        cate = cate,
                        defaults={
                            "content": content2,
                            "parent": current_item1
                        }
                    )
                if number3:
                    current_item, is_create = StandardItem.objects.get_or_create(
                            number = number3,
                            standard = sta,
                            cate = cate,
                            defaults={
                                "content": content3,
                                "parent": current_item2,
                                "level": level,
                                "method": method,
                                "full_score": full_score
                            }
                        )
                    if not is_create:
                        if content3:
                            current_item.content = current_item.content + ";" + content3
                            current_item.save()
                i += 1