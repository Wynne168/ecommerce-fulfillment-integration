"""最终只读核验：语法、文档/目录/证据一致性、文件链接、PDF越界及源指纹。
不修改业务数据，仅生成EVIDENCE/final_verification_record.md和验收JSON。
"""
import ast,csv,hashlib,json,os,re,zipfile
from pathlib import Path
import fitz
from docx import Document
import pymysql
ROOT=Path(__file__).resolve().parent.parent.parent
CFG=json.loads((ROOT/'SRC/governance/governance_config.json').read_text(encoding='utf-8'))
FACTS=json.loads((ROOT/'EVIDENCE/run_outputs/verified_facts.json').read_text(encoding='utf-8'))
CHECKS=[]
def chk(name,condition,detail):
    CHECKS.append(dict(name=name,passed=bool(condition),detail=detail))
    if not condition:raise AssertionError(name+': '+str(detail))
def squash(s):return re.sub(r'\s+','',s)
for p in (ROOT/'SRC/governance').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
ast.parse((ROOT/'TESTS/test_governance.py').read_text(encoding='utf-8'))
chk('Python语法',True,'全部交付Python可解析')
for m in FACTS['source_manifest']:
    h=hashlib.sha256()
    with (Path(CFG['data_dir'])/m['file']).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    chk('源指纹 '+m['file'],h.hexdigest()==m['sha256'],m['records'])
for p in (ROOT/'DOCS/REPORT_SECTIONS').glob('*.md'):
    word=ROOT/(p.stem+'.docx');pdf=ROOT/(p.stem+'.pdf')
    d=Document(word)
    xml=d.element
    alltext=''.join(xml.itertext())
    for name in re.findall(r'^#{1,4}\s+(.+)$',p.read_text(encoding='utf-8'),re.M):
        chk('Word章节 '+name,squash(name) in squash(alltext),word.name)
    with zipfile.ZipFile(word) as z:chk('Word结构 '+word.name,z.testzip() is None,{'tables':len(d.tables),'images':len(d.inline_shapes)})
    doc=fitz.open(pdf)
    text=''.join(pg.get_text() for pg in doc)
    required=['1950d777989f6a877539f53795b4c3c3','01cbdb2a8c075eaf248af643b3389f73'] if p.name.startswith(('报告2','演示')) else ['1550922','45','72']
    chk('PDF关键值 '+pdf.name,all(x in squash(text) for x in required),{'pages':len(doc),'characters':len(text)})
    bad=[]
    for n,pg in enumerate(doc):
        for block in pg.get_text('blocks'):
            if block[0]<-1 or block[1]<-1 or block[2]>pg.rect.width+1 or block[3]>pg.rect.height+1:bad.append(n+1)
    chk('PDF页面边界 '+pdf.name,not bad,'未发现文字块越出页面；首/中/末页另作视觉抽检')
for p in (ROOT/'DOCS').rglob('*.md'):
    for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if not target.startswith(('http','mailto:','#')):chk('文档链接 '+target,(p.parent/target).exists(),str(p.relative_to(ROOT)))
with (ROOT/'DOCS/GOVERNANCE/metadata_catalog.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
chk('元数据字段',len(rows)==72 and len({r['table_name'] for r in rows})==11,{'fields':len(rows),'objects':11})
chk('元数据批次',all(r['profiled_batch_id']==FACTS['batch_id'] for r in rows),FACTS['batch_id'])
sec=json.loads((ROOT/'EVIDENCE/run_outputs/security_verify_result.json').read_text(encoding='utf-8'))
chk('权限结果',len(sec['cases'])==19 and all(x['passed'] for x in sec['cases']),'19/19授权边界符合预期')
chk('审计缺口如实记录',sec['audit_rollback_risk']['issue_confirmed'],'事务回滚可撤销日志，未误标全面安全')
chk('评论正则残留',sec['privacy']['raw_phone']==2 and sec['privacy']['masked_phone_residual']==0,'电话2→0；不代表全隐私保证')
c=pymysql.connect(host=CFG['host'],port=CFG['port'],user=CFG['user'],password=os.environ[CFG['password_env']],database=CFG['database'],charset='utf8mb4',autocommit=True)
with c.cursor() as cur:
    cur.execute('SELECT COUNT(*) FROM v_delayed_orders_governed');chk('当前指标总数',cur.fetchone()[0]==6534,6534)
    cur.execute('SELECT COUNT(*) FROM v_delayed_orders');chk('A视图保留',cur.fetchone()[0]==7827,7827)
    cur.execute('SELECT batch_id FROM v_governance_current_batch');chk('当前批次一致',cur.fetchone()[0]==FACTS['batch_id'],FACTS['batch_id'])
    cur.execute("SELECT COUNT(*) FROM v_delayed_orders_governed WHERE quality_status='FLAGGED'");chk('标记延迟订单',cur.fetchone()[0]==36,36)
    cur.execute("SELECT COUNT(*) FROM mysql.user WHERE user LIKE 'gov\\_%%'");chk('演示账号清理',cur.fetchone()[0]==0,'无演示账号遗留')
    cur.execute('SELECT COUNT(*) FROM quality_check_summary WHERE batch_id=%s',(FACTS['batch_id'],));chk('批次质量汇总',cur.fetchone()[0]==45,45)
c.close()
browser=json.loads((ROOT/'EVIDENCE/run_outputs/browser_catalog_verification.json').read_text(encoding='utf-8'))
chk('浏览器筛选',browser['orders']==8 and browser['warnings']==22 and browser['steps']==7,browser)
# 不把未完成检查伪装为通过。
gaps=['Word文件内容/结构已查，Word自动导出PDF失败；PDF为独立ReportLab排版，实际Word分页未核验。',
'B业务页面接入、历史源快照、原子/并发发布、全流水线专用角色及不可回滚审计未完成。',
'OpenLineage事件只检查JSON可解析，未完整schema或接收端验证。',
'超时、时效、全部日期/文本边界、TLS/备份/删除等未逐项验证。']
(ROOT/'EVIDENCE/run_outputs/final_verification_result.json').write_text(json.dumps(dict(checks=CHECKS,gaps=gaps),ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 最终交付核验记录','',f'依据快照批次 `{FACTS["batch_id"]}`；核验脚本 `SRC/governance/verify_deliverables.py`。','',f'共{len(CHECKS)}个自动检查点通过；三份Word已重新打开读取结构，三份PDF已渲染首/中/末页抽检。','', '| 检查 | 结果 | 说明 |','|---|---|---|']
md.extend(f"| {x['name']} | 通过 | {str(x['detail']).replace('|','/')} |" for x in CHECKS)
md+=['','## 不能声称完成的部分','']+gaps
(ROOT/'EVIDENCE/final_verification_record.md').write_text('\n'.join(md),encoding='utf-8')
print('通过',len(CHECKS),'项最终检查')
