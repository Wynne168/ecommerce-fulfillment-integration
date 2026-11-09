"""根据已导出的真实批次证据生成质量报告；不连接或修改数据库。"""
import csv
import json
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
facts=json.loads((ROOT/'EVIDENCE/run_outputs/verified_facts.json').read_text(encoding='utf-8'))
quality=facts['quality'];bid=facts['batch_id']
counts=Counter(x['check_status'] for x in quality)
lines=['# 数据质量检查报告','',f'负责人：组员C。执行环境：MySQL {facts["version"]}、Python 3.15.0rc1；报告批次 `{bid}`。', '',
'本报告是 archive 全量 CSV 的实际检查结果，不是示例结果。两个全量批次的45条异常数量一致；主报告采用第二批次快照。源文件未改写，未修改 MYSQL 中 A/B 的既有文件。', '',
f'9个源文件合计 {sum(x["records"] for x in facts["source_manifest"]):,} 条数据记录（不含表头）。共45条质量规则：'+ '、'.join(f'{k}={v}' for k,v in counts.items())+'。批次 status=success 意味着运行完成且未触发观测升级，不意味着数据完全无异常。', '',
'## 1. 输入、隔离与输出行数','', '| 表 | CSV行数 | 暂存行数 | 隔离行数（去重计） | 核心行数 | 期望核心行数 | 核对 |', '|---|---:|---:|---:|---:|---:|---|']
for x in facts['reconciliation']:
    lines.append('| '+' | '.join(str(x.get(k)) if x.get(k) is not None else '-' for k in ['table_name','source_rows','staged_rows','quarantined_rows','core_rows','expected_core_rows','recon_status'])+' |')
lines+=['','geo 1000163→19015 是按邮编前缀聚合，不是98%数据损坏；评价99224−814=98410，是为兼容A的 review_id 主键隔离了后续记录。分类翻译表71行仅留在暂存层参与关联检查，A未建其核心表。', '',
'## 2. 45条规则实测','', '| 规则 | 表 | 检查行数（分母） | 异常数 | 异常率 | 阈值 | 状态 | 处置 | 样例键（最多5条） |','|---|---|---:|---:|---:|---:|---|---|---|']
for x in quality:
    keys=json.loads(x['sample_keys'] or '[]')
    lines.append(f"| {x['rule_id']} | {x['table_name']} | {x['checked_rows']} | {x['failed_rows']} | {float(x['fail_rate']):.4%} | {float(x['threshold_rate']):.4%} | {x['check_status']} | {x['disposal_action']} | {', '.join(keys) or '-'} |")
lines += ['', '规则条件、查询分母、对指标的影响见 [质量规则清单](quality_rules.md)，完整SQL见 `SQL/governance/02_quality_checks.sql`。异常数按规则分别计数，同一记录可命中多条规则，不能把上述数字相加当作异常订单数。', '',
'## 3. 重点解释与处置','',
'重复键：订单/客户/商品/卖家及明细、支付主键均无重复，评价却有814条“除首条外”的主键冲突。A的主键与源数据粒度不一致，不能未经复核断言后续评价是重复垃圾。临时隔离保存原始负载，建议A评估(review_id, order_id)联合主键。', '',
'关联失败：所有前向外键均为0异常，但775笔订单无明细、1笔无支付；INNER JOIN明细会丢掉这些订单。应保留主订单，标注无明细/无支付，而不是把金额缺失悄悄解释成真实0元。278条客户及7条卖家记录无邮编坐标，距离类分析应说明覆盖率。', '',
'条件缺失：delivered订单中8笔缺签收、14笔缺批准，shipped/delivered中2笔缺交承运；未送达状态有签收的6笔均为canceled。缺签收8笔从延迟天数分母排除，状态矛盾6笔标记而不自动改业务状态。', '',
'时间矛盾：166笔交承运早于下单、1359笔早于批准、23笔签收早于交承运；这些需要上游复核，不能简单交换日期制造“正确数据”。延迟视图附质量提示，未将所有时间标记订单自动排除。', '',
'金额核对：先对明细与支付分别按订单聚合，再比较 SUM(price+freight_value) 与 SUM(payment_value)，容差1.00下249筆异常。1.00是课堂复核阈值，不证明差异由分期利息造成；退款、优惠、截取缺失等原因尚无源字段支持。原验证脚本只比较price与payment会遗漏运费。', '',
'## 4. 履约指标口径核对','',f"已送达且签收/预计两日期非空的有效分母：{facts['delay_stats']['eligible_orders']}单。", '',
'| 口径 | 订单数 | 含义 |','|---|---:|---|',
'| A现有v_delayed_orders | 7827 | 所有状态且签收时刻>预计时刻 |',
'| 限定delivered、时刻比较 | 7826 | 去掉1笔canceled订单 |',
'| 限定delivered、DATEDIFF≥1 | 6534 | 同预计日期送达视为准时；治理候选口径 |',
'| 两种delivered口径差额 | 1292 | 预计日期当天、午夜之后签收，DATEDIFF=0 |','',
'新视图 v_delayed_orders_governed 与 A 原视图并存；未经组长确认，不替换B现有页面口径。天数口径延迟率=6534/96470≈6.7731%，时刻口径=7826/96470≈8.1124%；平均正延迟10.6201天、最大188天。', '',
'## 5. 复现与证据','',f'逐规则CSV：`EVIDENCE/quality_{bid}.csv`；行数CSV：`EVIDENCE/reconciliation_{bid}.csv`；日志CSV：`EVIDENCE/processing_{bid}.csv`。源文件SHA-256指纹与逐单血缘证据在 `EVIDENCE/run_outputs/verified_facts.json`。', '',
'质量明细 quality_check_results 每规则最多1000条（本批6058条）；完整异常数量存汇总表。例如geo异常981148条不是只1000条。完整隔离814行存 data_quarantine；标记保存在 data_quality_flags。详见 [处置说明](disposal_instructions.md)。', '',
'覆盖边界：45条规则不构成全面数据认证；没有验证全套非法日历日期、键trim后碰撞、维表空键、子表序号格式、坐标范围及并发。安全与隐私扫描见单独验证记录。']
(ROOT/'DOCS/GOVERNANCE/quality_report.md').write_text('\n'.join(lines),encoding='utf-8')
with (ROOT/'EVIDENCE/source_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','bytes','records','sha256']);w.writeheader()
    w.writerows({k:x[k] for k in ['file','bytes','records','sha256']} for x in facts['source_manifest'])
print('质量报告与源文件指纹目录已生成')
