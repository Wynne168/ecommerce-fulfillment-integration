"""独立排版PDF（ReportLab），不是Word导出。Word版式仍需用户在Word中检查。
读取三份Markdown；保留表格、代码、图片和外部链接；使用本机中文字体。
"""
import re
from html import escape
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).resolve().parent.parent.parent
pdfmetrics.registerFont(TTFont('Chinese','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('ChineseBold','C:/Windows/Fonts/simhei.ttf'))
styles={
 'body':ParagraphStyle('body',fontName='Chinese',fontSize=10.5,leading=16,spaceAfter=8,wordWrap='CJK'),
 'title':ParagraphStyle('title',fontName='ChineseBold',fontSize=21,leading=28,spaceAfter=16,wordWrap='CJK'),
 'h1':ParagraphStyle('h1',fontName='ChineseBold',fontSize=14,leading=20,spaceBefore=12,spaceAfter=8,wordWrap='CJK',keepWithNext=True,textColor=colors.HexColor('#244765')),
 'h2':ParagraphStyle('h2',fontName='ChineseBold',fontSize=12,leading=18,spaceBefore=10,spaceAfter=7,wordWrap='CJK',keepWithNext=True),
 'cell':ParagraphStyle('cell',fontName='Chinese',fontSize=8.3,leading=12,wordWrap='CJK'),
 'head':ParagraphStyle('head',fontName='ChineseBold',fontSize=8.5,leading=12,wordWrap='CJK',textColor=colors.white),
 'code':ParagraphStyle('code',fontName='Chinese',fontSize=8,leading=11,spaceAfter=9,backColor=colors.HexColor('#F0F4F8'),borderPadding=7,wordWrap='CJK'),
 'caption':ParagraphStyle('caption',fontName='Chinese',fontSize=9,leading=14,textColor=colors.grey,spaceAfter=10,wordWrap='CJK')}
WIDTH=A4[0]-84

def markup(text):
    s=escape(text.strip()).replace('&lt;br&gt;','<br/>')
    s=re.sub(r'\*\*([^*]+)\*\*',r'<font name="ChineseBold">\1</font>',s)
    s=re.sub(r'`([^`]+)`',r'<font color="#315473">\1</font>',s)
    def lk(m):
        label,url=m[1],m[2]
        return f'<link href="{url}" color="#245C97">{label}</link>' if url.startswith('http') else label+'（'+url+'）'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lk,s)

def footer(c,d):
    c.setFont('Chinese',8);c.setFillColor(colors.HexColor('#637181'))
    c.drawString(42,A4[1]-28,'INT6164 · 电商履约数据治理 · 组员C')
    c.drawRightString(A4[0]-42,24,f'第 {d.page} 页')

def convert(src):
    lines=src.read_text(encoding='utf-8').splitlines();story=[];i=0;first=True
    while i<len(lines):
        ln=lines[i]
        if not ln.strip():i+=1;continue
        if ln.startswith('```'):
            i+=1;block=[]
            while i<len(lines) and not lines[i].startswith('```'):
                # 保留缩进，CJK允许自动换行。
                block.append(escape(lines[i]).replace(' ','&#160;'));i+=1
            story.append(Paragraph('<br/>'.join(block),styles['code']));i+=1;continue
        if ln.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].startswith('|'):
                r=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?',x or '') for x in r):block.append(r)
                i+=1
            n=len(block[0]);weights=[]
            for col in range(n):
                longest=max(len(r[col]) for r in block if len(r)>col)
                weights.append(min(20,max(6,longest**0.5*2)))
            total=sum(weights);widths=[WIDTH*w/total for w in weights]
            cells=[[Paragraph(markup(s),styles['head' if j==0 else 'cell']) for s in r] for j,r in enumerate(block)]
            t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#244765')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F6F9')]),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#CBD5DF')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([t,Spacer(1,10)]);continue
        im=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',ln)
        if im:
            p=(src.parent/im[2]).resolve().with_suffix('.png')
            if p.exists():story.extend([Image(str(p),width=WIDTH,height=WIDTH*670/1100),Paragraph(im[1],styles['caption'])])
            i+=1;continue
        hd=re.match(r'^(#{1,4})\s+(.+)',ln)
        if hd:
            sty='title' if first else ('h1' if len(hd[1])<=2 else 'h2');story.append(Paragraph(markup(hd[2]),styles[sty]));first=False;i+=1;continue
        block=[ln];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|!\[)',lines[i]):block.append(lines[i]);i+=1
        story.append(Paragraph('<br/>'.join(markup(s) for s in block),styles['body']))
    out=ROOT/(src.stem+'.pdf')
    d=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=44,bottomMargin=40,title=lines[0].lstrip('# '),author='组员C')
    d.build(story,onFirstPage=footer,onLaterPages=footer)
    print(out.name,out.stat().st_size)
if __name__=='__main__':
    for p in sorted((ROOT/'DOCS/REPORT_SECTIONS').glob('*.md')):convert(p)
