import openpyxl
from pathlib import Path
from complexes.utils import slugify_name
wb = openpyxl.load_workbook(Path(r"C:\Users\user\Downloads\complexes_pp.xlsx"))
ws = wb.active
slugs = []
for row in ws.iter_rows(min_row=2, values_only=True):
    name = (row[0] or '').strip()
    if not name:
        continue
    urls = [cell for cell in row[1:] if isinstance(cell, str) and cell.strip()]
    if not urls:
        continue
    slug = slugify_name(name)
    if slug not in slugs:
        slugs.append(slug)
for slug in slugs:
    print(slug)
