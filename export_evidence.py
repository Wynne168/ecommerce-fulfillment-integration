"""只读导出治理结果、源文件指纹与演示证据；不更改数据库。
运行：设置 GOV_DB_PASSWORD 后 python SRC/governance/export_evidence.py
"""
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
import pymysql
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from rules import RULES
CFG = json.loads((HERE / 'governance_config.json').read_text(encoding='utf-8'))
OUT = ROOT / 'EVIDENCE'

def main():
    c = pymysql.connect(host=CFG['host'],port=CFG['port'],user=CFG['user'],password=os.environ[CFG['password_env']],database=CFG['database'],charset='utf8mb4',autocommit=True)
    def q(sql,args=None):
        with c.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql,args); return cur.fetchall()
    bid=q('SELECT batch_id FROM v_governance_current_batch')[0]['batch_id']
    ev={'batch_id':bid,'database':CFG['database'],'version':q('SELECT VERSION() version')[0]['version']}
    ev['quality']=q('SELECT * FROM quality_check_summary WHERE batch_id=%s ORDER BY summary_id',(bid,))
    ev['reconciliation']=q('SELECT * FROM batch_row_reconciliation WHERE batch_id=%s ORDER BY table_name',(bid,))
    ev['processing']=q('SELECT * FROM processing_log WHERE batch_id=%s ORDER BY log_id',(bid,))
    ev['times']=q('SELECT * FROM batch_data_time_profile WHERE batch_id=%s',(bid,))[0]
    ev['anomaly']=q("SELECT * FROM v_delay_days_trace WHERE order_id='1950d777989f6a877539f53795b4c3c3'")[0]
    ev['anomaly_flags']=q("SELECT * FROM data_quality_flags WHERE batch_id=%s AND record_key='1950d777989f6a877539f53795b4c3c3'",(bid,))
    ev['metric_example']=q("SELECT * FROM v_delay_days_trace WHERE order_id IN (SELECT order_id FROM v_delayed_orders_governed WHERE delay_days=15 AND quality_status='OK') ORDER BY order_id LIMIT 1")[0]
    ev['delay_stats']=q("SELECT COUNT(*) eligible_orders,SUM(DATEDIFF(order_delivered_customer_date,order_estimated_delivery_date)>=1) delayed_day,SUM(order_delivered_customer_date>order_estimated_delivery_date) delayed_timestamp,ROUND(AVG(CASE WHEN DATEDIFF(order_delivered_customer_date,order_estimated_delivery_date)>=1 THEN DATEDIFF(order_delivered_customer_date,order_estimated_delivery_date) END),6) avg_delay,MAX(DATEDIFF(order_delivered_customer_date,order_estimated_delivery_date)) max_delay FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL")[0]
    ev['source_manifest']=[]
    for f in sorted(Path(CFG['data_dir']).glob('*.csv')):
        h=hashlib.sha256()
        with f.open('rb') as fh:
            for chunk in iter(lambda:fh.read(1024*1024),b''): h.update(chunk)
        with f.open(encoding='utf-8-sig',newline='') as fh:
            reader=csv.reader(fh); fields=next(reader); n=sum(1 for _ in reader)
        ev['source_manifest'].append(dict(file=f.name,bytes=f.stat().st_size,sha256=h.hexdigest(),columns=fields,records=n))
    for name in ('quality','reconciliation','processing'):
        rows=ev[name]
        with (OUT/f'{name}_{bid}.csv').open('w',encoding='utf-8-sig',newline='') as fh:
            w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (OUT/'run_outputs'/'verified_facts.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    # SQL脚本与质量规则清单从相同规则定义导出
    sql=['-- 质量检查脚本（只读，返回异常数量和样例；由 rules.py 自动导出）', '-- 暂存层须已载入，结果写回由 governance_pipeline.py 执行。', '-- 注意每条规则的分母不同，详见规则清单。','']
    md=['# 质量规则清单','',f'规则版本 v1.0；共 {len(RULES)} 条。定义责任 C，表字段语义来自 A。首次全量检查批次 `{bid}`。', '', '判定：0 条异常为 PASS；有异常且异常率不超过阈值为 WARN；超过阈值为 FAIL。WARN 是已知问题仍须处置，不表示没有异常。阈值来自首次画像，仅为课堂初始值，不是业务 SLA。', '', '| 规则 | 名称/检查条件 | 表与字段 | 严重度 | 阈值 | 处置 | 指标影响 |','|---|---|---|---|---:|---|---|']
    for r in RULES:
        sql += [f"-- {r['rule_id']} {r['rule_name']}: {r['description']}",f"SELECT '{r['rule_id']}' rule_id, COUNT(*) failed_rows FROM ({r['sql']}) hits;",r['sql']+' ORDER BY src_row_num LIMIT 5;','']
        md.append(f"| {r['rule_id']} | {r['rule_name']}：{r['description'].replace('|','/')} | `{r['table']}` / {r['columns']} | {r['severity']} | {r['threshold']:.4%} | {r['action']} | {r['impact']} |")
    md += ['', '## 分母与可执行条件', '', '| 编号 | 分母查询 |','|---|---|']
    md += [f"| {r['rule_id']} | `{r['checked']}` |" for r in RULES]
    md += ['', '规则 SQL 见 `SQL/governance/02_quality_checks.sql`。异常明细最多写入每规则1000条，完整数量写入 quality_check_summary；不得用样例数代替异常总数。', '', 'geo 同邮编多坐标与重复 customer_unique_id 不应被当作源数据垃圾：前者是源文件粒度与 A 主键不一致，后者是正常跨订单客户。review_id 冲突也需 A 复核模型；隔离后续行只是兼容现有主键的临时策略。', '', '覆盖局限：暂存层原始键尚未统一 trim 后判重；子表序号格式、关键维表空键、坐标范围与评论敏感信息没有纳入45条SQL规则。隐私扫描另由 security_verify.py 执行。']
    (ROOT/'SQL/governance/02_quality_checks.sql').write_text('\n'.join(sql),encoding='utf-8')
    (ROOT/'DOCS/GOVERNANCE/quality_rules.md').write_text('\n'.join(md),encoding='utf-8')
    c.close()
    print(json.dumps({'batch_id':bid,'delay_stats':ev['delay_stats'],'anomaly':ev['anomaly'],'metric_example':ev['metric_example'],'source_records':sum(x['records'] for x in ev['source_manifest'])},ensure_ascii=False,indent=2,default=str))
if __name__=='__main__':main()
