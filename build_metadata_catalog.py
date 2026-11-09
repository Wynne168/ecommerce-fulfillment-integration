"""
元数据目录生成 - 电商履约数据整合系统
负责人：组员C

在组员A《数据字典》的基础上，为每个字段补充：字段来源（源文件/源字段）、转换规则、质量要求、关联质量规则、
敏感级别与隐私处理；数据类型/可空/键从 information_schema 实际读取，空值率/去重数/取值范围从当前核心表实时画像。

输出：
    1. 数据库表 metadata_catalog（可用 SQL 查询）
    2. DOCS/GOVERNANCE/metadata_catalog.html（单文件可查看页面，支持搜索与筛选）
    3. DOCS/GOVERNANCE/metadata_catalog.csv（便于导入 Excel / 数据目录工具）

用法：
    set GOV_DB_PASSWORD=******
    python SRC/governance/build_metadata_catalog.py
"""

import csv
import html
import json
import os
import sys
from pathlib import Path

import pymysql

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from rules import RULES  # noqa: E402

CFG = json.loads((HERE / "governance_config.json").read_text(encoding="utf-8"))
OUT_DIR = ROOT / "DOCS" / "GOVERNANCE"

TS = "STR_TO_DATE('%Y-%m-%d %H:%i:%s')；订单日期另有 DOM-07 检查；其他表日期未验证全套异常边界"
TRIM = "TRIM；空串 → NULL"
DEC = "TRIM 后校验数字格式，CAST AS DECIMAL(10,2)"
INT = "TRIM；空串 → NULL；CAST AS SIGNED"

# 表级信息：说明、粒度、源文件、刷新方式
TABLES = {
    "orders": ("订单主表", "一行一笔订单", "olist_orders_dataset.csv", "每批全量重建；隔离 DUP-01/REF-06/NUL-06 命中行"),
    "order_items": ("订单明细表", "一行一个订单商品项", "olist_order_items_dataset.csv", "每批全量重建；隔离 DUP-03/REF-01~03/DOM-05 及级联"),
    "order_payments": ("订单支付表", "一行一笔支付", "olist_order_payments_dataset.csv", "每批全量重建；隔离 DUP-04/REF-04 及级联"),
    "customers": ("客户信息表", "一行一个客户会话（customer_id）", "olist_customers_dataset.csv", "每批全量重建；隔离 DUP-02"),
    "sellers": ("卖家信息表", "一行一个卖家", "olist_sellers_dataset.csv", "每批全量重建；隔离 DUP-07"),
    "products": ("商品信息表", "一行一个商品", "olist_products_dataset.csv", "每批全量重建；隔离 DUP-06"),
    "reviews": ("客户评价表", "一行一条评价（review_id 唯一）", "olist_order_reviews_dataset.csv",
                "每批全量重建；DUP-05 同一 review_id 多订单时隔离后续行（建议主键改为 review_id+order_id）"),
    "geolocation": ("地理位置表", "一行一个邮编前缀", "olist_geolocation_dataset.csv", "每批全量重建；DUP-08 按邮编聚合（经纬度取平均）"),
    "processing_log": ("处理日志表（系统表）", "一行一个处理步骤", "governance_pipeline.py 运行时写入", "追加；每步 running→success/failed"),
    "quality_check_results": ("质量检查明细表（系统表）", "一行一条异常记录", "governance_pipeline.py 运行时写入", "追加；每规则每批最多 1000 条明细"),
    "v_delayed_orders_governed": ("治理口径延迟订单视图", "一行一笔延迟订单", "由 orders/customers/data_quality_flags 计算", "视图，实时"),
}

# 字段级补充：(业务定义[A], 源字段, 转换规则, 质量要求, 敏感级别, 隐私处理)
COLS = {
    "orders": {
        "order_id": ("订单唯一标识", "order_id", TRIM, "非空、唯一", "L2", "伪匿名哈希，内部可见"),
        "customer_id": ("客户ID（会话级）", "customer_id", TRIM, "非空、必须存在于 customers", "L2", "伪匿名；对外视图不输出"),
        "order_status": ("订单状态", "order_status", "TRIM + LOWER", "取值属于 8 种实际状态", "L1", "-"),
        "order_purchase_timestamp": ("客户下单时间（业务发生时间）", "order_purchase_timestamp", TS, "非空", "L2", "-"),
        "order_approved_at": ("支付批准时间", "order_approved_at", TS, "delivered 时非空；>= 下单时间", "L2", "-"),
        "order_delivered_carrier_date": ("移交承运商时间", "order_delivered_carrier_date", TS, "shipped/delivered 时非空；>= 下单、>= 批准", "L2", "-"),
        "order_delivered_customer_date": ("客户实际签收时间", "order_delivered_customer_date", TS,
                                          "delivered 时非空；非 delivered 时应为空；>= 交承运", "L2", "-"),
        "order_estimated_delivery_date": ("预计送达日期（均为 00:00:00）", "order_estimated_delivery_date", TS, "非空；>= 下单时间", "L2", "-"),
    },
    "order_items": {
        "order_id": ("订单ID", "order_id", TRIM, "必须存在于 orders", "L2", "-"),
        "order_item_id": ("订单内商品序号", "order_item_id", "CAST AS UNSIGNED", "与 order_id 组合唯一", "L1", "-"),
        "product_id": ("商品ID", "product_id", TRIM, "必须存在于 products", "L1", "-"),
        "seller_id": ("卖家ID", "seller_id", TRIM, "必须存在于 sellers", "L2", "商家只能看到本卖家（v_merchant_order_items）"),
        "shipping_limit_date": ("卖家发货限制日期", "shipping_limit_date", TS, "可空", "L2", "-"),
        "price": ("商品价格", "price", DEC, "> 0", "L2", "-"),
        "freight_value": ("运费（多商品时分摊）", "freight_value", DEC, ">= 0", "L2", "-"),
    },
    "order_payments": {
        "order_id": ("订单ID", "order_id", TRIM, "必须存在于 orders", "L2", "-"),
        "payment_sequential": ("支付序号", "payment_sequential", "CAST AS UNSIGNED", "与 order_id 组合唯一", "L1", "-"),
        "payment_type": ("支付方式", "payment_type", "TRIM + LOWER", "属于 credit_card/boleto/voucher/debit_card", "L1", "-"),
        "payment_installments": ("分期期数", "payment_installments", "CAST AS SIGNED；无法解析 → 0", ">= 1", "L2", "-"),
        "payment_value": ("该笔支付金额", "payment_value", DEC + "；无法解析 → 0", "> 0；订单合计与商品+运费差 <= 1.00", "L2", "-"),
    },
    "customers": {
        "customer_id": ("客户ID（会话ID）", "customer_id", TRIM, "非空、唯一", "L2", "伪匿名；对外视图不输出"),
        "customer_unique_id": ("客户唯一标识（跨订单识别同一人）", "customer_unique_id", TRIM, "可空", "L3",
                               "持久伪匿名标识，可串联个人购买历史；仅治理/运行角色可见"),
        "customer_zip_code_prefix": ("邮编前5位", "customer_zip_code_prefix", "TRIM，保留前导 0（按字符串处理）",
                                     "5 位数字；应能关联 geolocation", "L3", "准标识符；客服视图截断为前 3 位"),
        "customer_city": ("城市名", "customer_city", "TRIM + LOWER", "可空", "L2", "准标识符；与邮编组合时 19% 客户 k<5"),
        "customer_state": ("州代码", "customer_state", "TRIM + UPPER", "两位大写字母", "L1", "聚合分析最小粒度"),
    },
    "sellers": {
        "seller_id": ("卖家ID", "seller_id", TRIM, "非空、唯一", "L2", "行级授权依据"),
        "seller_zip_code_prefix": ("邮编前5位", "seller_zip_code_prefix", "TRIM，按字符串保留前导 0", "应能关联 geolocation", "L2", "商户地址信息，内部可见"),
        "seller_city": ("城市名", "seller_city", "TRIM + LOWER", "可空", "L1", "-"),
        "seller_state": ("州代码", "seller_state", "TRIM + UPPER", "两位大写字母", "L1", "-"),
    },
    "products": {
        "product_id": ("商品ID", "product_id", TRIM, "非空、唯一", "L1", "-"),
        "product_category_name": ("商品分类（葡萄牙语）", "product_category_name", TRIM, "非空；应能找到英文翻译", "L1", "-"),
        "product_name_lenght": ("商品名称字符数（源字段拼写保留）", "product_name_lenght", INT, "可空", "L1", "-"),
        "product_description_lenght": ("商品描述字符数", "product_description_lenght", INT, "可空", "L1", "-"),
        "product_photos_qty": ("商品图片数量", "product_photos_qty", INT, "可空", "L1", "-"),
        "product_weight_g": ("重量（克）", "product_weight_g", INT, "> 0", "L1", "-"),
        "product_length_cm": ("长度（厘米）", "product_length_cm", INT, "> 0", "L1", "-"),
        "product_height_cm": ("高度（厘米）", "product_height_cm", INT, "> 0", "L1", "-"),
        "product_width_cm": ("宽度（厘米）", "product_width_cm", INT, "> 0", "L1", "-"),
    },
    "reviews": {
        "review_id": ("评价ID", "review_id", TRIM, "唯一（源数据不满足，见 DUP-05）", "L2", "-"),
        "order_id": ("订单ID", "order_id", TRIM, "必须存在于 orders", "L2", "-"),
        "review_score": ("评分 1-5", "review_score", "CAST AS SIGNED", "属于 1..5", "L2", "-"),
        "review_comment_title": ("评价标题", "review_comment_title", "TRIM；空串 → NULL；截断至 200 字符", "可空", "L3", "自由文本，可能含个人信息"),
        "review_comment_message": ("评价内容", "review_comment_message", "TRIM；空串 → NULL", "可空", "L3",
                                   "实测含电话 2 条、网址 2 条；分析用 v_reviews_masked 脱敏"),
        "review_creation_date": ("评价创建时间", "review_creation_date", TS, ">= 订单下单时间", "L2", "-"),
        "review_answer_timestamp": ("卖家回复时间", "review_answer_timestamp", TS, ">= 评价创建时间", "L2", "-"),
    },
    "geolocation": {
        "geolocation_zip_code_prefix": ("邮编前5位", "geolocation_zip_code_prefix", "TRIM；GROUP BY 邮编（DUP-08）", "非空、唯一（聚合后）", "L1", "公开邮政数据"),
        "geolocation_lat": ("纬度", "geolocation_lat", "同一邮编多行取 AVG，保留 8 位小数", "非空", "L1", "邮编级坐标，非个人位置"),
        "geolocation_lng": ("经度", "geolocation_lng", "同一邮编多行取 AVG，保留 8 位小数", "非空", "L1", "邮编级坐标，非个人位置"),
        "geolocation_city": ("城市名", "geolocation_city", "取该邮编首行；TRIM + LOWER", "可空", "L1", "-"),
        "geolocation_state": ("州代码", "geolocation_state", "取该邮编首行；TRIM + UPPER", "可空", "L1", "-"),
    },
    "processing_log": {
        "log_id": ("日志ID", "-", "自增", "唯一", "L1", "-"),
        "batch_id": ("批次编号 batch_YYYYMMDD_HHMMSS", "-", "流水线生成", "非空；关联所有治理结果", "L1", "-"),
        "process_name": ("处理步骤名", "-", "stage_load.* / quality_check / core_build.* / observability", "非空", "L1", "-"),
        "start_time": ("开始时间（处理时间，非业务时间）", "-", "NOW()", "非空", "L1", "-"),
        "end_time": ("结束时间", "-", "NOW()", "step 结束时必须回写（OBS-RUN-02）", "L1", "-"),
        "input_rows": ("输入行数", "-", "源 CSV 记录数 / 暂存行数", "与 output_rows 共同用于行数守恒", "L1", "-"),
        "output_rows": ("输出行数", "-", "实际写入行数（COUNT 实测，而非沿用输入数）", "-", "L1", "-"),
        "status": ("状态 running/success/partial/failed", "-", "-", "非空", "L1", "-"),
        "error_message": ("错误摘要", "-", "-", "failed/partial 时非空", "L1", "-"),
    },
    "quality_check_results": {
        "check_id": ("检查ID", "-", "自增", "唯一", "L1", "-"),
        "batch_id": ("关联批次", "-", "-", "非空", "L1", "-"),
        "check_name": ("规则编号（如 NUL-04）", "-", "= quality_rules.rule_id", "非空", "L1", "-"),
        "table_name": ("被检查表", "-", "-", "非空", "L1", "-"),
        "record_id": ("异常记录键", "-", "业务键，截断至 50 字符", "-", "L2", "-"),
        "issue_type": ("问题类别", "-", "重复键/关联失败/条件缺失/时间顺序/域值范围/一致性/口径", "非空", "L1", "-"),
        "issue_description": ("问题描述 + src_row_num", "-", "-", "-", "L1", "-"),
        "severity": ("严重程度", "-", "critical/warning/info", "非空", "L1", "-"),
        "checked_at": ("检查时间", "-", "NOW()", "非空", "L1", "-"),
    },
    "v_delayed_orders_governed": {
        "delay_days": ("延迟天数（核心履约指标）", "orders.order_delivered_customer_date, orders.order_estimated_delivery_date",
                       "DATEDIFF(签收时间, 预计送达日期)；仅 delivered 且两日期非空且 >= 1", "整数 >= 1", "L2", "见 lineage_delay_days.md"),
        "late_by_timestamp": ("签收时刻是否晚于预计时刻（口径对照）", "同上", "签收时间 > 预计送达时间", "-", "L2", "-"),
        "flag_rules": ("该订单当前批次命中的质量规则", "data_quality_flags.rule_id", "GROUP_CONCAT", "-", "L1", "-"),
        "quality_status": ("质量状态 OK/FLAGGED", "data_quality_flags", "有标记 → FLAGGED", "-", "L1", "-"),
    },
}


ORDER_TS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
            "order_delivered_customer_date", "order_estimated_delivery_date"]
# 跨表或列名无法直接匹配的规则 → 字段映射
EXTRA = {("orders", c): ["DOM-07"] for c in ORDER_TS}
EXTRA.update({("order_payments", "payment_value"): ["CON-01"], ("order_items", "price"): ["CON-01"],
              ("order_items", "freight_value"): ["CON-01"], ("orders", "order_id"): ["REF-07", "REF-08", "CON-01"]})


def rules_for(table, col):
    if table == "v_delayed_orders_governed":
        return "NUL-01,NUL-04,NUL-05,DOM-07,TIM-04,TIM-05,TIM-06,CON-02" if col == "delay_days" else ""
    ids = set(EXTRA.get((table, col), []))
    for r in RULES:
        cols = [x.strip() for x in r["columns"].split(",")]
        if r["table"] == table and col in cols:
            ids.add(r["rule_id"])
    return ",".join(sorted(ids))


def main():
    db = CFG["database"]
    c = pymysql.connect(host=CFG["host"], port=CFG["port"], user=CFG["user"], password=os.environ[CFG["password_env"]],
                        database=db, charset="utf8mb4", autocommit=True)
    cur = c.cursor()
    cur.execute("SELECT batch_id FROM v_governance_current_batch")
    batch = cur.fetchone()[0]
    entries, table_meta = [], []
    for t, cols in COLS.items():
        cur.execute("SELECT COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION", (db, t))
        info = {r[0]: r for r in cur.fetchall()}
        cur.execute("SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND REFERENCED_TABLE_NAME IS NOT NULL", (db, t))
        fks = {r[0]: f"FK→{r[1]}.{r[2]}" for r in cur.fetchall()}
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        n = cur.fetchone()[0]
        desc, grain, src, refresh = TABLES[t]
        table_meta.append(dict(table=t, description=desc, grain=grain, source=src, refresh=refresh, rows=n,
                               columns=len(cols)))
        for col, (definition, src_col, transform, qreq, sens, privacy) in cols.items():
            name, pos, ctype, nullable, key = info[col]
            key_txt = " ".join(x for x in ["PK" if key == "PRI" else "", fks.get(col, "")] if x) or "-"
            cur.execute(f"SELECT CAST(SUM(`{col}` IS NULL) AS DECIMAL(20,10))/COUNT(*), COUNT(DISTINCT `{col}`), MIN(`{col}`), MAX(`{col}`) FROM `{t}`")
            nr, dc, mn, mx = cur.fetchone()
            if sens == "L3" or ctype.startswith(("text", "varchar(200)")):
                mn, mx = "（敏感/自由文本，不展示）", "（敏感/自由文本，不展示）"
            e = dict(table_name=t, column_name=col, ordinal_position=pos, data_type=ctype, is_nullable=nullable,
                     key_type=key_txt, business_definition=definition,
                     source_file=src if src_col != "-" and not src_col.startswith(("orders.", "data_quality")) else
                     ("由视图计算" if t.startswith("v_") else "系统生成"),
                     source_column=src_col, transform_rule=transform, quality_requirement=qreq,
                     quality_rule_ids=rules_for(t, col), sensitivity_level=sens, privacy_handling=privacy,
                     definition_owner="组员A" if not t.startswith("v_") and t not in ("processing_log",) else ("组员B" if t == "processing_log" else "组员C"),
                     quality_owner="组员C", null_rate=round(float(nr or 0), 6), distinct_count=int(dc or 0),
                     min_value=None if mn is None else str(mn)[:100], max_value=None if mx is None else str(mx)[:100],
                     profiled_batch_id=batch)
            entries.append(e)
    # 写入数据库
    cur.execute("DELETE FROM metadata_catalog")
    keys = list(entries[0].keys())
    cur.executemany(f"INSERT INTO metadata_catalog ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))})",
                    [[e[k] for k in keys] for e in entries])
    # 规则与最新批次结果
    cur.execute("SELECT r.rule_id, r.rule_name, r.category, r.table_name, r.column_names, r.severity, r.disposal_action, "
                "r.threshold_rate, s.checked_rows, s.failed_rows, s.fail_rate, s.check_status FROM quality_rules r "
                "LEFT JOIN quality_check_summary s ON s.rule_id=r.rule_id AND s.batch_id=%s ORDER BY r.rule_id", (batch,))
    rules = [dict(zip(["rule_id", "rule_name", "category", "table", "columns", "severity", "action", "threshold", "checked",
                       "failed", "rate", "status"], [x if not hasattr(x, "as_tuple") else float(x) for x in r])) for r in cur.fetchall()]
    cur.execute("SELECT step_no, layer_name, object_name, field_names, rule_text, condition_text, owner FROM metric_lineage "
                "WHERE metric_id='delay_days' ORDER BY step_no")
    lineage = [dict(zip(["step", "layer", "object", "fields", "rule", "condition", "owner"], r)) for r in cur.fetchall()]
    cur.execute("SELECT process_started_at, process_status, business_time_min, business_time_max FROM batch_data_time_profile WHERE batch_id=%s", (batch,))
    bt = cur.fetchone()
    c.close()

    with open(OUT_DIR / "metadata_catalog.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(entries)
    write_html(entries, table_meta, rules, lineage, batch, bt)
    print(f"元数据目录：{len(entries)} 个字段 / {len(table_meta)} 张表/视图，批次 {batch}")


def write_html(entries, tables, rules, lineage, batch, bt):
    data = json.dumps(dict(entries=entries, tables=tables, rules=rules, lineage=lineage), ensure_ascii=False, default=str)
    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>元数据目录 · 电商履约数据整合系统</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1f2933;--muted:#616e7c;--line:#e4e7eb;--accent:#2563eb;--l1:#16a34a;--l2:#d97706;--l3:#dc2626}}
*{{box-sizing:border-box}} body{{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);font-size:14px}}
header{{background:#111827;color:#fff;padding:22px 32px}} header h1{{margin:0 0 6px;font-size:22px}} header p{{margin:0;color:#cbd2d9;font-size:13px}}
main{{padding:20px 32px 48px;max-width:1500px;margin:auto}}
.tabs{{display:flex;gap:6px;margin-bottom:16px}} .tabs button{{border:1px solid var(--line);background:#fff;padding:8px 14px;border-radius:6px;cursor:pointer;font-size:14px}}
.tabs button.on{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin-bottom:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;cursor:pointer}}
.card:hover{{border-color:var(--accent)}} .card h3{{margin:0 0 4px;font-size:15px}} .card .meta{{color:var(--muted);font-size:12px;line-height:1.6}}
.filters{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}}
input,select{{padding:7px 10px;border:1px solid var(--line);border-radius:6px;font-size:14px;background:#fff}} input{{min-width:280px}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:6px}} table{{width:100%;min-width:1350px;border-collapse:collapse;background:#fff;border:1px solid var(--line)}}
th,td{{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;font-size:13px}}
th{{background:#f0f2f5;position:sticky;top:0;z-index:1;white-space:nowrap}} tr:hover td{{background:#fafbff}}
code{{background:#f0f2f5;padding:1px 4px;border-radius:3px;font-size:12px}}
.badge{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:12px;color:#fff;font-weight:600}}
.L1{{background:var(--l1)}} .L2{{background:var(--l2)}} .L3{{background:var(--l3)}}
.PASS{{color:var(--l1);font-weight:600}} .WARN{{color:var(--l2);font-weight:600}} .FAIL,.ERROR{{color:var(--l3);font-weight:600}}
.rule{{display:inline-block;margin:1px 3px 1px 0;padding:0 5px;border:1px solid #c7d2fe;border-radius:4px;background:#eef2ff;font-size:12px;cursor:help}}
.muted{{color:var(--muted)}} .num{{text-align:right;white-space:nowrap}} .hide{{display:none}}
.flow{{display:flex;flex-direction:column;gap:8px;max-width:980px}} .step{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px}}
.step b{{color:var(--accent)}} .note{{background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:10px 14px;margin:12px 0;max-width:980px}}
</style></head><body>
<header><h1>元数据目录 · 电商履约数据整合系统</h1>
<p>数据库 ecommerce_fulfillment ｜ 画像批次 <b>{html.escape(batch)}</b> ｜ 处理时间 {bt[0]}（状态 {bt[1]}）｜ 业务时间范围（下单）{bt[2]} ~ {bt[3]} ｜ 字段定义：组员A ｜ 来源/转换/质量/敏感级别：组员C</p></header>
<main>
<div class="tabs"><button class="on" data-tab="cols">字段目录</button><button data-tab="rules">质量规则（45）</button><button data-tab="lin">指标血缘：延迟天数</button></div>
<section id="cols">
<div class="cards" id="cards"></div>
<div class="filters"><input id="q" placeholder="搜索字段名、定义、来源、规则编号，例如 delivered / NUL-04 / L3">
<select id="ft"><option value="">全部表/视图</option></select>
<select id="fs"><option value="">全部敏感级别</option><option>L1</option><option>L2</option><option>L3</option></select>
<span class="muted" id="cnt"></span></div>
<div class="wrap"><table><thead><tr><th>表</th><th>字段</th><th>类型</th><th>可空</th><th>键</th><th>业务定义</th><th>源文件 / 源字段</th><th>转换规则</th><th>质量要求</th><th>质量规则</th><th>敏感</th><th>隐私处理</th><th class="num">空值率</th><th class="num">去重数</th><th>最小值 ~ 最大值</th></tr></thead><tbody id="tb"></tbody></table></div>
<p class="muted">敏感级别：<span class="badge L1">L1</span> 公开/低敏 · <span class="badge L2">L2</span> 内部（伪匿名ID、金额、时间）· <span class="badge L3">L3</span> 敏感（可串联个人或含自由文本个人信息）。空值率与取值范围为当前批次核心表实测值。</p>
</section>
<section id="rules" class="hide">
<div class="filters"><input id="rq" placeholder="搜索规则编号、名称、表"><select id="rc"><option value="">全部类别</option></select><select id="rs"><option value="">全部状态</option><option>PASS</option><option>WARN</option><option>FAIL</option></select></div>
<div class="wrap"><table><thead><tr><th>编号</th><th>名称</th><th>类别</th><th>表</th><th>字段</th><th>严重度</th><th>处置</th><th class="num">检查行数</th><th class="num">异常行数</th><th class="num">异常率</th><th class="num">阈值</th><th>状态</th></tr></thead><tbody id="rb"></tbody></table></div>
</section>
<section id="lin" class="hide">
<div class="note">延迟天数 = DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)，仅统计 order_status='delivered'、两个日期非空且结果 ≥ 1 的订单。逐单追溯请查询视图 <code>v_delay_days_trace</code>，详见 DOCS/GOVERNANCE/lineage_delay_days.md。</div>
<div class="flow" id="flow"></div>
</section>
</main>
<script>
const D={data};
const $=s=>document.querySelector(s);
const esc=s=>(s===null||s===undefined)?'':String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const ruleTip={{}}; D.rules.forEach(r=>ruleTip[r.rule_id]=r.rule_name+'｜'+r.category+'｜最新批次：'+r.status+' 异常 '+r.failed);
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
 ['cols','rules','lin'].forEach(id=>$('#'+id).classList.toggle('hide',id!==b.dataset.tab));}});
$('#cards').innerHTML=D.tables.map(t=>`<div class="card" data-t="${{t.table}}"><h3>${{t.table}}</h3><div class="meta">${{esc(t.description)}}<br>粒度：${{esc(t.grain)}}<br>来源：${{esc(t.source)}}<br>行数：<b>${{t.rows.toLocaleString()}}</b> ｜ 已编目字段：${{t.columns}}<br>${{esc(t.refresh)}}</div></div>`).join('');
D.tables.forEach(t=>$('#ft').insertAdjacentHTML('beforeend',`<option>${{t.table}}</option>`));
document.querySelectorAll('.card').forEach(c=>c.onclick=()=>{{$('#ft').value=c.dataset.t;render();}});
function render(){{const q=$('#q').value.toLowerCase(),ft=$('#ft').value,fs=$('#fs').value;
 const rows=D.entries.filter(e=>(!ft||e.table_name===ft)&&(!fs||e.sensitivity_level===fs)&&(!q||JSON.stringify(e).toLowerCase().includes(q)));
 $('#cnt').textContent=`共 ${{rows.length}} 个字段`;
 $('#tb').innerHTML=rows.map(e=>`<tr><td>${{e.table_name}}</td><td><b>${{e.column_name}}</b></td><td><code>${{esc(e.data_type)}}</code></td><td>${{e.is_nullable}}</td><td>${{esc(e.key_type)}}</td><td>${{esc(e.business_definition)}}</td><td>${{esc(e.source_file)}}<br><span class="muted">${{esc(e.source_column)}}</span></td><td>${{esc(e.transform_rule)}}</td><td>${{esc(e.quality_requirement)}}</td><td>${{(e.quality_rule_ids||'').split(',').filter(Boolean).map(r=>`<span class="rule" title="${{esc(ruleTip[r]||'')}}">${{r}}</span>`).join('')||'-'}}</td><td><span class="badge ${{e.sensitivity_level}}">${{e.sensitivity_level}}</span></td><td>${{esc(e.privacy_handling)}}</td><td class="num">${{(e.null_rate*100).toFixed(2)}}%</td><td class="num">${{e.distinct_count.toLocaleString()}}</td><td class="muted">${{esc(e.min_value)}} ~ ${{esc(e.max_value)}}</td></tr>`).join('');}}
['#q','#ft','#fs'].forEach(s=>$(s).addEventListener('input',render)); render();
[...new Set(D.rules.map(r=>r.category))].forEach(c=>$('#rc').insertAdjacentHTML('beforeend',`<option>${{c}}</option>`));
function renderRules(){{const q=$('#rq').value.toLowerCase(),c=$('#rc').value,s=$('#rs').value;
 $('#rb').innerHTML=D.rules.filter(r=>(!c||r.category===c)&&(!s||r.status===s)&&(!q||JSON.stringify(r).toLowerCase().includes(q))).map(r=>`<tr><td><b>${{r.rule_id}}</b></td><td>${{esc(r.rule_name)}}</td><td>${{r.category}}</td><td>${{r.table}}</td><td><code>${{esc(r.columns)}}</code></td><td>${{r.severity}}</td><td>${{r.action}}</td><td class="num">${{(r.checked||0).toLocaleString()}}</td><td class="num">${{(r.failed||0).toLocaleString()}}</td><td class="num">${{((r.rate||0)*100).toFixed(4)}}%</td><td class="num">${{((r.threshold||0)*100).toFixed(4)}}%</td><td class="${{r.status}}">${{r.status}}</td></tr>`).join('');}}
['#rq','#rc','#rs'].forEach(s=>$(s).addEventListener('input',renderRules)); renderRules();
$('#flow').innerHTML=D.lineage.map(l=>`<div class="step"><b>${{l.step}}. ${{esc(l.layer)}}</b> — <code>${{esc(l.object)}}</code>（${{esc(l.owner)}}）<br>字段：${{esc(l.fields)}}<br>规则：${{esc(l.rule)}}<br><span class="muted">条件：${{esc(l.condition)}}</span></div>`).join('<div style="text-align:center;color:#9aa5b1">↓</div>');
</script></body></html>"""
    (OUT_DIR / "metadata_catalog.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
