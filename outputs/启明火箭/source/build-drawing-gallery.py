from pathlib import Path
import json
root=Path(__file__).resolve().parent.parent
out=root/'library/source-drawings'
m=json.loads((out/'index.json').read_text())
assert len(m['rows'])==13
for r in m['rows']:assert (out/r['image']).is_file()
rows=[{'physical_pdf_page':r['physical_pdf_page'],'image':r['image']} for r in m['rows']]
template=(root/'source/drawing-gallery-template.html').read_text()
(out/'原图纸浏览.html').write_text(template.replace('__ROWS__',json.dumps(rows,ensure_ascii=False)))
print('Rebuilt Chinese display-name drawing gallery; 13 existing source display images unchanged.')
