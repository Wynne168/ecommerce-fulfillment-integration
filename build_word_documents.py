"""将三个Markdown主文档转换为可编辑Word。需要python-docx；保留表格、代码、图片及外链。
输出位于交付包根目录。PDF由单独Word渲染步骤生成。
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
ROOT=Path(__file__).resolve().parent.parent.parent
SOURCES=ROOT/'DOCS/REPORT_SECTIONS'

def font(style,name='宋体',size=11):
    style.font.name=name;style.font.size=Pt(size)
    style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),name)

def shade(cell,fill):
    e=OxmlElement('w:shd');e.set(qn('w:fill'),fill);cell._tc.get_or_add_tcPr().append(e)

def link(p,text,url):
    h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'245C97');pr.append(color)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u);r.append(pr);t=OxmlElement('w:t');t.text=text;r.append(t);h.append(r);p._p.append(h)

def inline(p,text):
    text=text.replace('<br>','\n').strip()
    pat=r'(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*)'
    for part in re.split(pat,text):
        if not part:continue
        if part.startswith('[') and '](' in part:
            m=re.match(r'\[([^\]]+)\]\(([^)]+)\)',part);link(p,m[1],m[2])
        elif part.startswith('`'):
            r=p.add_run(part[1:-1]);r.font.name='Consolas';r.font.size=Pt(9)
        elif part.startswith('**'):p.add_run(part[2:-2]).bold=True
        else:p.add_run(part)

def table(doc,lines):
    parsed=[[x.strip() for x in ln.strip().strip('|').split('|')] for ln in lines]
    parsed=[r for r in parsed if not all(re.fullmatch(r':?-{3,}:?',x or '') for x in r)]
    if not parsed:return
    n=max(map(len,parsed));t=doc.add_table(rows=1,cols=n);t.style='Table Grid';t.autofit=True
    for j,s in enumerate(parsed[0]):
        inline(t.rows[0].cells[j].paragraphs[0],s);shade(t.rows[0].cells[j],'244765')
        for run in t.rows[0].cells[j].paragraphs[0].runs:run.font.color.rgb=RGBColor(255,255,255);run.bold=True
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row_no,r in enumerate(parsed[1:],1):
        cells=t.add_row().cells
        for j,s in enumerate(r):inline(cells[j].paragraphs[0],s)
        if row_no%2==0:
            for cell in cells:shade(cell,'F0F4F8')
    for row in t.rows:
        cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3);p.paragraph_format.line_spacing=1.08
                for run in p.runs:run.font.size=Pt(9)
    doc.add_paragraph().paragraph_format.space_after=Pt(2)

def convert(src):
    doc=Document();sec=doc.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(1.8);sec.right_margin=Cm(1.8)
    font(doc.styles['Normal']);doc.styles['Normal'].paragraph_format.line_spacing=1.25;doc.styles['Normal'].paragraph_format.space_after=Pt(6)
    for name,size in [('Title',22),('Heading 1',16),('Heading 2',13),('Heading 3',11)]:
        font(doc.styles[name],'黑体',size);doc.styles[name].font.color.rgb=RGBColor.from_string('244765')
    code=doc.styles.add_style('Code Block',WD_STYLE_TYPE.PARAGRAPH);font(code,'Consolas',8.5);code.paragraph_format.line_spacing=1.0;code.paragraph_format.space_after=Pt(8)
    header=sec.header.paragraphs[0];header.add_run('INT6164 · 电商履约数据治理 · 组员C').font.size=Pt(9)
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('第 ');field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field);footer.add_run(' 页')
    lines=src.read_text(encoding='utf-8').splitlines();i=0;first=True
    while i<len(lines):
        ln=lines[i]
        if not ln.strip():i+=1;continue
        if ln.startswith('```'):
            i+=1;block=[]
            while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
            p=doc.add_paragraph(style='Code Block');p.add_run('\n'.join(block))
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'F1F4F7');p._p.get_or_add_pPr().append(sh);i+=1;continue
        if ln.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
            table(doc,block);continue
        im=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',ln)
        if im:
            path=(src.parent/im[2]).resolve()
            if path.suffix=='.svg':path=path.with_suffix('.png')
            if path.exists():doc.add_picture(str(path),width=Cm(17.4));doc.add_paragraph(im[1],style='Caption')
            else:doc.add_paragraph('图示见：'+im[2])
            i+=1;continue
        hd=re.match(r'^(#{1,4})\s+(.+)',ln)
        if hd:
            level=len(hd[1]);p=doc.add_paragraph(style='Title' if first and level==1 else f'Heading {min(level-1 if level>1 else 1,3)}');inline(p,hd[2]);first=False;i+=1;continue
        # 每段可以包含多个连续文字行；保留Markdown硬换行。
        block=[ln.rstrip()];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|!\[)',lines[i]):block.append(lines[i].rstrip());i+=1
        p=doc.add_paragraph();inline(p,'\n'.join(block))
    doc.core_properties.author='组员C';doc.core_properties.title=lines[0].lstrip('# ');doc.core_properties.subject='数据治理与验证；2026-11-09快照'
    out=ROOT/(src.stem+'.docx');doc.save(out)
    check=Document(out)
    assert len(check.paragraphs)>10
    if src.name.startswith('报告'):assert len(check.tables)>0
    print(out.name,'paragraphs',len(check.paragraphs),'tables',len(check.tables),'images',len(check.inline_shapes))
    return out
if __name__=='__main__':
    for p in sorted(SOURCES.glob('*.md')):convert(p)
