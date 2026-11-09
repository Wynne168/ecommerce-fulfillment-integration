"""
数据治理流水线 - 电商履约数据整合系统
负责人：组员C

流程（每次运行 = 一个批次 batch_id，全部结果可按 batch_id 关联）：
    1. stage_load   ：原始 CSV 按原样载入暂存层 stg_*，记录源行数 / 暂存行数 / 行号
    2. quality_check：执行 rules.py 中的质量规则，写 quality_check_summary（汇总）
                      与 quality_check_results（A 定义的明细表，check_name = rule_id）
    3. disposal     ：按规则处置——quarantine 写入 data_quarantine（不进入核心表），
                      flag 写入 data_quality_flags（保留并标记），fix 在核心表构建时修正；
                      子表随被隔离的父订单级联隔离（CAS-01）
    4. core_build   ：TRUNCATE 并重建 A 的核心业务表（外键检查开启，作为第二道防线）
    5. reconcile    ：行数守恒核对 batch_row_reconciliation
    6. observability：按 05_observability_rules.sql 的规则评估，写 observability_events
    7. export       ：输出运行摘要 JSON 与 OpenLineage 格式的血缘事件 JSON

每个步骤都在 processing_log（A 定义、B 负责采集）中写入 running -> success/failed 的完整生命周期。

用法：
    set GOV_DB_PASSWORD=******
    python SRC/governance/governance_pipeline.py --init          # 首次：建库、A 的核心表、治理表、视图
    python SRC/governance/governance_pipeline.py                 # 运行一个批次
    python SRC/governance/governance_pipeline.py --database ecommerce_fulfillment_govtest \
           --data-dir DATA/TEST --batch-prefix test --no-baseline --init   # 测试库

依赖：pip install pymysql
"""

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import RULES, D, N  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SQL_DIR = ROOT / "SQL" / "governance"

# 源文件 -> 暂存表列（顺序即 CSV 表头顺序）
SOURCES = {
    "customers": ("olist_customers_dataset.csv",
                  ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"]),
    "sellers": ("olist_sellers_dataset.csv",
                ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"]),
    "products": ("olist_products_dataset.csv",
                 ["product_id", "product_category_name", "product_name_lenght", "product_description_lenght",
                  "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm",
                  "product_width_cm"]),
    "geolocation": ("olist_geolocation_dataset.csv",
                    ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city",
                     "geolocation_state"]),
    "orders": ("olist_orders_dataset.csv",
               ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
                "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]),
    "order_items": ("olist_order_items_dataset.csv",
                    ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price",
                     "freight_value"]),
    "order_payments": ("olist_order_payments_dataset.csv",
                       ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"]),
    "reviews": ("olist_order_reviews_dataset.csv",
                ["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message",
                 "review_creation_date", "review_answer_timestamp"]),
    "category_translation": ("product_category_name_translation.csv",
                             ["product_category_name", "product_category_name_english"]),
}
# 核心表（A 的模型）按外键依赖顺序
CORE_ORDER = ["customers", "sellers", "products", "geolocation", "orders", "order_items", "order_payments", "reviews"]
# 缺失即无法继续的源
REQUIRED_SOURCES = set(CORE_ORDER)


def now():
    return dt.datetime.now().replace(microsecond=0)


class Pipeline:
    def __init__(self, cfg, args):
        self.cfg = cfg
        self.args = args
        self.db = args.database or cfg["database"]
        self.data_dir = Path(args.data_dir or cfg["data_dir"])
        if not self.data_dir.is_absolute():
            self.data_dir = (ROOT / self.data_dir).resolve()
        self.password = os.environ.get(cfg["password_env"])
        if self.password is None:
            sys.exit(f"请先设置环境变量 {cfg['password_env']}（数据库密码不写入配置文件）")
        self.evidence_dir = (HERE / cfg["evidence_dir"]).resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.batch_id = f"{args.batch_prefix}_{now():%Y%m%d_%H%M%S}"
        self.started_at = now()
        self.step_status = {}      # step -> status
        self.source_rows = {}      # table -> csv rows
        self.stage_errors = {}     # table -> message
        self.rule_results = []
        self.conn = None

    # ---------------- 基础设施 ----------------
    def connect(self, with_db=True):
        conn = pymysql.connect(host=self.cfg["host"], port=self.cfg["port"], user=self.cfg["user"],
                               password=self.password, database=self.db if with_db else None,
                               charset="utf8mb4", autocommit=True)
        with conn.cursor() as cur:
            # 非严格模式：非法日期等由质量规则先行发现并修正为 NULL，而非让整批写入失败
            cur.execute("SET SESSION sql_mode = 'NO_ENGINE_SUBSTITUTION'")
            cur.execute("SET SESSION group_concat_max_len = 65535")
        return conn

    def q(self, sql, args=None, fetch="all"):
        with self.conn.cursor() as cur:
            cur.execute(sql, args)
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
            if fetch == "scalar":
                row = cur.fetchone()
                return row[0] if row else None
            return cur.rowcount

    def lit(self, value):
        return self.conn.escape(value)

    def run_sql_file(self, path, prefix=""):
        content = Path(path).read_text(encoding="utf-8")
        env = dict(os.environ, MYSQL_PWD=self.password)
        cmd = [self.cfg["mysql_bin"], f"-h{self.cfg['host']}", f"-P{self.cfg['port']}", f"-u{self.cfg['user']}",
               "--default-character-set=utf8mb4", self.db]
        res = subprocess.run(cmd, input=prefix + content, text=True, encoding="utf-8",
                             capture_output=True, env=env)
        if res.returncode != 0:
            raise RuntimeError(f"执行 {path} 失败: {res.stderr.strip()}")
        return res.stdout

    # ---------------- processing_log（运行批次记录） ----------------
    def log_start(self, process_name, input_rows=None):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO processing_log (batch_id, process_name, start_time, input_rows, status) "
                        "VALUES (%s, %s, %s, %s, 'running')", (self.batch_id, process_name, now(), input_rows))
            return cur.lastrowid

    def log_end(self, log_id, status, output_rows=None, input_rows=None, error=None):
        self.q("UPDATE processing_log SET end_time=%s, status=%s, output_rows=%s, "
               "input_rows=COALESCE(%s, input_rows), error_message=%s WHERE log_id=%s",
               (now(), status, output_rows, input_rows, error, log_id), fetch=None)

    # ---------------- 初始化 ----------------
    def init(self):
        root_conn = self.connect(with_db=False)
        with root_conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        root_conn.close()
        self.conn = self.connect()
        has_core = self.q("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name='orders'",
                          (self.db,), fetch="scalar")
        if not has_core or self.args.rebuild_core:
            # A 的建表脚本：其 DROP 顺序在表已存在时会触发外键错误，因此关闭外键检查后执行（不修改 A 的文件）
            self.run_sql_file(self.cfg["core_ddl"], prefix="SET FOREIGN_KEY_CHECKS=0;\n")
            self.q("SET FOREIGN_KEY_CHECKS=1", fetch=None)
            print(f"[init] 已执行组员A建表脚本: {self.cfg['core_ddl']}")
        for f in ["01_governance_schema.sql", "04_lineage_delay_days.sql", "05_observability_rules.sql"]:
            self.run_sql_file(SQL_DIR / f)
            print(f"[init] 已执行 {f}")

    # ---------------- 1. 暂存层载入 ----------------
    def stage_load(self, table):
        fname, cols = SOURCES[table]
        path = self.data_dir / fname
        log_id = self.log_start(f"stage_load.{table}")
        self.q(f"TRUNCATE TABLE stg_{table}", fetch=None)
        if not path.exists():
            msg = f"源文件不存在: {path}"
            self.stage_errors[table] = msg
            self.log_end(log_id, "failed", 0, 0, msg)
            self.step_status[f"stage_load.{table}"] = "failed"
            return
        placeholders = ", ".join(["%s"] * (len(cols) + 3))
        sql = (f"INSERT INTO stg_{table} (src_row_num, batch_id, src_file, {', '.join(cols)}) "
               f"VALUES ({placeholders})")
        n_rows, malformed, buf = 0, [], []
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if header != cols:
                msg = f"表头与预期不一致: 实际={header} 预期={cols}"
                self.stage_errors[table] = msg
                self.log_end(log_id, "failed", 0, 0, msg[:1000])
                self.step_status[f"stage_load.{table}"] = "failed"
                return
            with self.conn.cursor() as cur:
                for rec in reader:
                    n_rows += 1
                    if len(rec) != len(cols):
                        malformed.append(n_rows)
                        continue
                    buf.append([n_rows, self.batch_id, fname] + [v if v.strip() != "" else None for v in rec])
                    if len(buf) >= 5000:
                        cur.executemany(sql, buf)
                        buf = []
                if buf:
                    cur.executemany(sql, buf)
        self.source_rows[table] = n_rows
        staged = self.q(f"SELECT COUNT(*) FROM stg_{table}", fetch="scalar")
        err = None
        status = "success"
        if malformed:
            status = "partial"
            err = f"{len(malformed)} 行列数不符被跳过，样例行号: {malformed[:5]}"
            self.stage_errors[table] = err
        self.log_end(log_id, status, staged, n_rows, err)
        self.step_status[f"stage_load.{table}"] = status
        print(f"[stage] {table:<22} source={n_rows:>8} staged={staged:>8} {status}")

    # ---------------- 2/3. 质量检查与处置 ----------------
    def upsert_rules(self):
        with self.conn.cursor() as cur:
            for r in RULES:
                cur.execute(
                    "REPLACE INTO quality_rules (rule_id, rule_name, category, table_name, column_names, description, "
                    "check_sql, severity, threshold_rate, disposal_action, metric_impact) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (r["rule_id"], r["rule_name"], r["category"], r["table"], r["columns"], r["description"],
                     r["sql"], r["severity"], r["threshold"], r["action"], r["impact"]))

    def run_quality_checks(self):
        log_id = self.log_start("quality_check", input_rows=len(RULES))
        self.upsert_rules()
        cap = int(self.cfg.get("detail_cap_per_rule", 1000))
        bid = self.lit(self.batch_id)
        ok = 0
        for r in RULES:
            t0 = time.time()
            res = dict(rule_id=r["rule_id"], table=r["table"], severity=r["severity"], action=r["action"],
                       threshold=r["threshold"], checked=0, failed=0, rate=0.0, status="ERROR", samples=[], error=None)
            try:
                self.q("DROP TEMPORARY TABLE IF EXISTS tmp_rule_hits", fetch=None)
                self.q(f"CREATE TEMPORARY TABLE tmp_rule_hits (INDEX idx_row (src_row_num)) AS {r['sql']}", fetch=None)
                failed = self.q("SELECT COUNT(*) FROM tmp_rule_hits", fetch="scalar")
                checked = self.q(r["checked"], fetch="scalar") or 0
                rate = failed / checked if checked else 0.0
                status = "PASS" if failed == 0 else ("WARN" if rate <= r["threshold"] else "FAIL")
                samples = [x[0] for x in self.q("SELECT record_key FROM tmp_rule_hits ORDER BY src_row_num LIMIT 5")]
                desc = self.lit(r["rule_name"])
                written = self.q(
                    f"INSERT INTO quality_check_results (batch_id, check_name, table_name, record_id, issue_type, "
                    f"issue_description, severity, checked_at) "
                    f"SELECT {bid}, {self.lit(r['rule_id'])}, {self.lit(r['table'])}, LEFT(record_key, 50), "
                    f"{self.lit(r['category'])}, CONCAT({desc}, '; src_row_num=', src_row_num), "
                    f"{self.lit(r['severity'])}, NOW() FROM tmp_rule_hits ORDER BY src_row_num LIMIT {cap}",
                    fetch=None) if failed else 0
                if failed and r["action"] == "quarantine":
                    self.quarantine_from_tmp(r)
                if failed and (r["action"] == "flag" or r["rule_id"] == "DOM-07"):
                    self.q(f"INSERT INTO data_quality_flags (batch_id, rule_id, table_name, record_key, src_row_num, severity) "
                           f"SELECT {bid}, {self.lit(r['rule_id'])}, {self.lit(r['table'])}, record_key, src_row_num, "
                           f"{self.lit(r['severity'])} FROM tmp_rule_hits", fetch=None)
                res.update(checked=checked, failed=failed, rate=rate, status=status, samples=samples, written=written)
                ok += 1
            except Exception as e:  # 规则 SQL 出错也要被观测到（OBS-QUA-04）
                res["error"] = str(e)[:500]
                res["written"] = 0
            res["ms"] = int((time.time() - t0) * 1000)
            self.q("INSERT INTO quality_check_summary (batch_id, rule_id, table_name, checked_rows, failed_rows, fail_rate, "
                   "threshold_rate, check_status, severity, disposal_action, sample_keys, detail_rows_written, duration_ms, "
                   "error_message) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (self.batch_id, r["rule_id"], r["table"], res["checked"], res["failed"], round(res["rate"], 6),
                    r["threshold"], res["status"], r["severity"], r["action"], json.dumps(res["samples"]),
                    res["written"], res["ms"], res["error"]), fetch=None)
            self.rule_results.append(res)
            print(f"[check] {r['rule_id']:<7} {res['status']:<5} failed={res['failed']:>7} / {res['checked']:>8} "
                  f"({res['rate']:.4%}) {r['action']}")
        status = "success" if ok == len(RULES) else "partial"
        self.log_end(log_id, status, ok, None, None if ok == len(RULES) else f"{len(RULES) - ok} 条规则执行出错")
        self.step_status["quality_check"] = status

    def payload_expr(self, table, alias="s"):
        cols = SOURCES[table][1]
        parts = ", ".join(f"'{c}', {alias}.{c}" for c in cols)
        return f"JSON_OBJECT('src_file', {alias}.src_file, 'src_row_num', {alias}.src_row_num, {parts})"

    def quarantine_from_tmp(self, r):
        t = r["table"]
        self.q(f"INSERT INTO data_quarantine (batch_id, rule_id, table_name, src_row_num, record_key, raw_payload, reason) "
               f"SELECT {self.lit(self.batch_id)}, {self.lit(r['rule_id'])}, {self.lit(t)}, s.src_row_num, h.record_key, "
               f"{self.payload_expr(t)}, {self.lit(r['rule_name'])} "
               f"FROM tmp_rule_hits h JOIN stg_{t} s ON s.src_row_num = h.src_row_num", fetch=None)

    def cascade_quarantine(self):
        """父订单被隔离且没有保留副本时，其明细/支付/评价级联隔离（CAS-01）。"""
        log_id = self.log_start("disposal.cascade")
        bid = self.lit(self.batch_id)
        total = 0
        kept_orders = (f"SELECT so.order_id FROM stg_orders so WHERE NOT EXISTS (SELECT 1 FROM data_quarantine q "
                       f"WHERE q.batch_id={bid} AND q.table_name='orders' AND q.src_row_num=so.src_row_num)")
        for child, key in [("order_items", "CONCAT(s.order_id,'#',s.order_item_id)"),
                           ("order_payments", "CONCAT(s.order_id,'#',s.payment_sequential)"),
                           ("reviews", "s.review_id")]:
            n = self.q(
                f"INSERT INTO data_quarantine (batch_id, rule_id, table_name, src_row_num, record_key, raw_payload, reason) "
                f"SELECT {bid}, 'CAS-01', '{child}', s.src_row_num, {key}, {self.payload_expr(child)}, '父订单已隔离，级联隔离' "
                f"FROM stg_{child} s WHERE s.order_id IN (SELECT q.record_key FROM data_quarantine q "
                f"WHERE q.batch_id={bid} AND q.table_name='orders') AND s.order_id NOT IN ({kept_orders}) "
                f"AND NOT EXISTS (SELECT 1 FROM data_quarantine q2 WHERE q2.batch_id={bid} AND q2.table_name='{child}' "
                f"AND q2.src_row_num=s.src_row_num)", fetch=None)
            total += n
        quarantined = self.q("SELECT COUNT(*) FROM data_quarantine WHERE batch_id=%s", (self.batch_id,), fetch="scalar")
        self.log_end(log_id, "success", quarantined, None, f"级联隔离 {total} 行；本批隔离区共 {quarantined} 行")
        self.step_status["disposal.cascade"] = "success"

    # ---------------- 4. 核心表构建（含 fix 规则） ----------------
    def notq(self, table, alias="s"):
        return (f"NOT EXISTS (SELECT 1 FROM data_quarantine q WHERE q.batch_id={self.lit(self.batch_id)} "
                f"AND q.table_name='{table}' AND q.src_row_num={alias}.src_row_num)")

    def core_sql(self):
        def ni(c):
            return f"CAST(NULLIF(TRIM(s.{c}), '') AS SIGNED)"
        return {
            "customers": f"""INSERT INTO customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
                SELECT TRIM(s.customer_id), NULLIF(TRIM(s.customer_unique_id),''), NULLIF(TRIM(s.customer_zip_code_prefix),''),
                       NULLIF(LOWER(TRIM(s.customer_city)),''), NULLIF(UPPER(TRIM(s.customer_state)),'')
                FROM stg_customers s WHERE {self.notq('customers')}""",
            "sellers": f"""INSERT INTO sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state)
                SELECT TRIM(s.seller_id), NULLIF(TRIM(s.seller_zip_code_prefix),''), NULLIF(LOWER(TRIM(s.seller_city)),''),
                       NULLIF(UPPER(TRIM(s.seller_state)),'')
                FROM stg_sellers s WHERE {self.notq('sellers')}""",
            "products": f"""INSERT INTO products (product_id, product_category_name, product_name_lenght, product_description_lenght,
                       product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
                SELECT TRIM(s.product_id), NULLIF(TRIM(s.product_category_name),''), {ni('product_name_lenght')},
                       {ni('product_description_lenght')}, {ni('product_photos_qty')}, {ni('product_weight_g')},
                       {ni('product_length_cm')}, {ni('product_height_cm')}, {ni('product_width_cm')}
                FROM stg_products s WHERE {self.notq('products')}""",
            # DUP-08 fix：按邮编前缀聚合，经纬度取平均，城市/州取该前缀首行
            "geolocation": f"""INSERT INTO geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
                SELECT TRIM(f.geolocation_zip_code_prefix), a.lat, a.lng, NULLIF(LOWER(TRIM(f.geolocation_city)),''),
                       NULLIF(UPPER(TRIM(f.geolocation_state)),'')
                FROM (SELECT s.geolocation_zip_code_prefix AS zip, MIN(s.src_row_num) AS first_row,
                             ROUND(AVG(CAST(s.geolocation_lat AS DECIMAL(12,8))), 8) AS lat,
                             ROUND(AVG(CAST(s.geolocation_lng AS DECIMAL(12,8))), 8) AS lng
                      FROM stg_geolocation s WHERE {self.notq('geolocation')} AND s.geolocation_zip_code_prefix IS NOT NULL
                      GROUP BY s.geolocation_zip_code_prefix) a
                JOIN stg_geolocation f ON f.src_row_num = a.first_row""",
            # DOM-07 fix：无法解析的时间戳修正为 NULL（已在 data_quality_flags 标记）
            "orders": f"""INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at,
                       order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)
                SELECT TRIM(s.order_id), TRIM(s.customer_id), NULLIF(LOWER(TRIM(s.order_status)),''),
                       {D('s.order_purchase_timestamp')}, {D('s.order_approved_at')}, {D('s.order_delivered_carrier_date')},
                       {D('s.order_delivered_customer_date')}, {D('s.order_estimated_delivery_date')}
                FROM stg_orders s WHERE {self.notq('orders')}""",
            "order_items": f"""INSERT INTO order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
                SELECT TRIM(s.order_id), CAST(TRIM(s.order_item_id) AS UNSIGNED), TRIM(s.product_id), TRIM(s.seller_id),
                       {D('s.shipping_limit_date')}, {N('s.price', 'DECIMAL(10,2)')}, {N('s.freight_value', 'DECIMAL(10,2)')}
                FROM stg_order_items s WHERE {self.notq('order_items')}""",
            "order_payments": f"""INSERT INTO order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value)
                SELECT TRIM(s.order_id), CAST(TRIM(s.payment_sequential) AS UNSIGNED), LOWER(TRIM(s.payment_type)),
                       COALESCE({N('s.payment_installments', 'SIGNED')}, 0), COALESCE({N('s.payment_value', 'DECIMAL(10,2)')}, 0)
                FROM stg_order_payments s WHERE {self.notq('order_payments')}""",
            "reviews": f"""INSERT INTO reviews (review_id, order_id, review_score, review_comment_title, review_comment_message,
                       review_creation_date, review_answer_timestamp)
                SELECT TRIM(s.review_id), TRIM(s.order_id), {N('s.review_score', 'SIGNED')}, LEFT(NULLIF(TRIM(s.review_comment_title),''), 200),
                       NULLIF(TRIM(s.review_comment_message),''), {D('s.review_creation_date')}, {D('s.review_answer_timestamp')}
                FROM stg_reviews s WHERE {self.notq('reviews')}""",
        }

    def build_core(self):
        self.q("SET FOREIGN_KEY_CHECKS=0", fetch=None)
        for t in reversed(CORE_ORDER):
            self.q(f"TRUNCATE TABLE {t}", fetch=None)
        self.q("SET FOREIGN_KEY_CHECKS=1", fetch=None)   # 写入时开启外键检查，作为质量规则之外的第二道防线
        sqls = self.core_sql()
        for t in CORE_ORDER:
            staged = self.q(f"SELECT COUNT(*) FROM stg_{t}", fetch="scalar")
            log_id = self.log_start(f"core_build.{t}", input_rows=staged)
            try:
                n = self.q(sqls[t], fetch=None)
                self.log_end(log_id, "success", n)
                self.step_status[f"core_build.{t}"] = "success"
                print(f"[core ] {t:<22} rows={n}")
            except Exception as e:
                self.log_end(log_id, "failed", 0, None, str(e)[:1000])
                self.step_status[f"core_build.{t}"] = "failed"
                print(f"[core ] {t:<22} FAILED: {e}")

    # ---------------- 5. 行数守恒 ----------------
    def reconcile(self):
        log_id = self.log_start("reconcile")
        for t, (fname, _) in SOURCES.items():
            if t in self.stage_errors and t not in self.source_rows:
                self.q("REPLACE INTO batch_row_reconciliation (batch_id, table_name, source_file, recon_status, note) "
                       "VALUES (%s,%s,%s,'MISSING',%s)", (self.batch_id, t, fname, self.stage_errors[t][:255]), fetch=None)
                continue
            staged = self.q(f"SELECT COUNT(*) FROM stg_{t}", fetch="scalar")
            quarantined = self.q("SELECT COUNT(DISTINCT src_row_num) FROM data_quarantine WHERE batch_id=%s AND table_name=%s",
                                 (self.batch_id, t), fetch="scalar")
            if t == "category_translation":
                core, expected, note = None, None, "A 的模型无对应核心表，仅用于 REF-11 检查"
            elif t == "geolocation":
                core = self.q("SELECT COUNT(*) FROM geolocation", fetch="scalar")
                expected = self.q(f"SELECT COUNT(DISTINCT geolocation_zip_code_prefix) FROM stg_geolocation s "
                                  f"WHERE {self.notq('geolocation')}", fetch="scalar")
                note = "DUP-08 修正：按邮编前缀聚合，期望行数 = 去重后邮编数"
            else:
                core = self.q(f"SELECT COUNT(*) FROM {t}", fetch="scalar")
                expected = staged - quarantined
                note = None
            src = self.source_rows.get(t)
            ok = (src == staged) and (expected is None or core == expected)
            self.q("REPLACE INTO batch_row_reconciliation VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (self.batch_id, t, fname, src, staged, quarantined, core, expected, "OK" if ok else "MISMATCH",
                    note), fetch=None)
        self.log_end(log_id, "success", len(SOURCES))
        self.step_status["reconcile"] = "success"

    # ---------------- 6. 可观测性 ----------------
    def event(self, rule, obj, metric, observed, expected, status, severity, msg):
        self.q("INSERT INTO observability_events (batch_id, obs_rule_id, object_name, metric_name, observed_value, "
               "expected_value, event_status, severity, message) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (self.batch_id, rule, obj, metric, None if observed is None else str(observed),
                None if expected is None else str(expected), status, severity, msg[:500]), fetch=None)

    def previous_batch(self):
        return self.q("SELECT batch_id FROM batch_data_time_profile WHERE batch_id <> %s AND batch_id LIKE %s "
                      "AND process_status IN ('success','partial') ORDER BY process_finished_at DESC LIMIT 1",
                      (self.batch_id, self.args.batch_prefix + "\\_%"), fetch="scalar")

    def evaluate_observability(self):
        log_id = self.log_start("observability")
        c = self.cfg
        prev = self.previous_batch()
        # OBS-RUN-01 步骤失败
        failed = self.q("SELECT process_name, error_message FROM processing_log WHERE batch_id=%s AND status='failed'",
                        (self.batch_id,))
        for name, err in failed:
            self.event("OBS-RUN-01", name, "step_status", "failed", "success", "ALERT", "critical", f"{name} 失败: {err}")
        if not failed:
            self.event("OBS-RUN-01", "pipeline", "failed_steps", 0, 0, "OK", "critical", "本批次无失败步骤")
        # OBS-RUN-02 长时间 running（任意批次，包括其他成员脚本遗留）
        stuck = self.q("SELECT batch_id, process_name, start_time FROM processing_log WHERE status='running' "
                       "AND batch_id <> %s AND start_time < NOW() - INTERVAL %s MINUTE",
                       (self.batch_id, c["stuck_running_minutes"]))
        for b, name, st in stuck:
            self.event("OBS-RUN-02", f"{b}/{name}", "running_since", st, f"<{c['stuck_running_minutes']}min", "WARN",
                       "warning", f"批次 {b} 的 {name} 自 {st} 起一直为 running，可能进程中断未回写状态")
        if not stuck:
            self.event("OBS-RUN-02", "processing_log", "stuck_running_steps", 0, 0, "OK", "warning", "无长时间 running 的步骤")
        # OBS-RUN-03 / ROW-01 / ROW-02 / ROW-03
        base = c.get("baseline_row_counts", {}) if not self.args.no_baseline else {}
        for t, src, staged, quarantined, core, expected, status, note in self.q(
                "SELECT table_name, source_rows, staged_rows, quarantined_rows, core_rows, expected_core_rows, recon_status, note "
                "FROM batch_row_reconciliation WHERE batch_id=%s", (self.batch_id,)):
            if status == "MISSING":
                self.event("OBS-RUN-03", t, "source_file", "missing", "present", "ALERT", "critical", note or "源文件缺失")
                continue
            self.event("OBS-ROW-01", t, "source_vs_staged", staged, src, "OK" if src == staged else "ALERT", "critical",
                       f"源 {src} 行，暂存 {staged} 行")
            if expected is not None:
                self.event("OBS-ROW-02", t, "core_vs_expected", core, expected, "OK" if core == expected else "ALERT",
                           "critical", f"核心 {core} 行，期望 {expected} 行（暂存 {staged} - 隔离 {quarantined}）")
            ref, ref_name = None, None
            if prev:
                ref = self.q("SELECT staged_rows FROM batch_row_reconciliation WHERE batch_id=%s AND table_name=%s",
                             (prev, t), fetch="scalar")
                ref_name = f"上一成功批次 {prev}"
            if ref is None and t in base:
                ref, ref_name = base[t], "基线(dataREADME)"
            if ref:
                drift = (staged - ref) / ref
                st = "ALERT" if abs(drift) > c["row_drift_alert"] else ("WARN" if abs(drift) > c["row_drift_warn"] else "OK")
                self.event("OBS-ROW-03", t, "row_drift_rate", f"{drift:.2%}", f"±{c['row_drift_warn']:.0%}", st, "warning",
                           f"暂存 {staged} 行，参照 {ref} 行（{ref_name}）")
        # OBS-QUA-01/02/04 质量结果
        for rule_id, status, sev, failed_rows, rate, thr, err in self.q(
                "SELECT rule_id, check_status, severity, failed_rows, fail_rate, threshold_rate, error_message "
                "FROM quality_check_summary WHERE batch_id=%s", (self.batch_id,)):
            if status == "ERROR":
                self.event("OBS-QUA-04", rule_id, "check_error", "ERROR", "PASS/WARN", "ALERT", "critical", f"规则执行出错: {err}")
            elif status == "FAIL" and sev == "critical":
                self.event("OBS-QUA-01", rule_id, "failed_rows", failed_rows, 0, "ALERT", "critical",
                           f"关键规则失败 {failed_rows} 行（已按规则隔离/标记）")
            elif status == "FAIL":
                self.event("OBS-QUA-02", rule_id, "fail_rate", f"{float(rate):.4%}", f"<={float(thr):.4%}", "WARN", "warning",
                           f"异常率超过阈值，异常 {failed_rows} 行")
        summ = self.q("SELECT check_status, COUNT(*) FROM quality_check_summary WHERE batch_id=%s GROUP BY check_status",
                      (self.batch_id,))
        self.event("OBS-QUA-01", "quality_check", "status_distribution", json.dumps(dict(summ)), None, "OK", "info",
                   "本批质量规则状态分布")
        # OBS-QUA-03 相对上一批突变
        if prev:
            for rule_id, cur_n, prev_n in self.q(
                    "SELECT a.rule_id, a.failed_rows, b.failed_rows FROM quality_check_summary a "
                    "JOIN quality_check_summary b ON b.rule_id=a.rule_id AND b.batch_id=%s WHERE a.batch_id=%s",
                    (prev, self.batch_id)):
                diff = abs(cur_n - prev_n)
                if diff >= 10 and (prev_n == 0 or diff / prev_n > c["quality_drift_warn"]):
                    self.event("OBS-QUA-03", rule_id, "failed_rows_change", cur_n, prev_n, "WARN", "warning",
                               f"异常数从 {prev_n} 变为 {cur_n}")
        # OBS-FRS-01 / 02：处理时间与业务时间分别评估
        last_ok = self.q("SELECT MAX(process_finished_at) FROM batch_data_time_profile WHERE process_status IN ('success','partial')",
                         fetch="scalar")
        # 只在下一批运行时检查与上次完成的时间差；独立定时探测器尚未部署。
        gap_hours = max(0.0, (self.started_at - last_ok).total_seconds()/3600) if last_ok else 0.0
        self.event("OBS-FRS-01", "pipeline", "hours_since_last_process", f"{gap_hours:.4f}",
                   f"<={c['freshness_hours']}h", "WARN" if gap_hours>c['freshness_hours'] else "OK", "warning",
                   f"本批开始于 {self.started_at}；上一次完成于 {last_ok}；首批无历史则记0，不代表独立定时监控已部署")
        biz_max = self.q("SELECT MAX(order_purchase_timestamp) FROM orders", fetch="scalar")
        if prev:
            prev_max = self.q("SELECT business_time_max FROM batch_data_time_profile WHERE batch_id=%s", (prev,), fetch="scalar")
            st = "WARN" if (biz_max and prev_max and biz_max < prev_max) else "OK"
            self.event("OBS-FRS-02", "orders", "business_time_max", biz_max, f">={prev_max}", st, "warning",
                       "业务时间（下单时间）只用于判断数据是否回退，不用于判断处理是否及时")
        else:
            self.event("OBS-FRS-02", "orders", "business_time_max", biz_max, None, "OK", "warning",
                       "首个批次，记录业务时间上界作为后续比较基准")
        # OBS-MET-01 指标守护：延迟订单数
        try:
            delayed = self.q("SELECT COUNT(*) FROM v_delayed_orders_governed", fetch="scalar")
            prev_val = None
            if prev:
                prev_val = self.q("SELECT observed_value FROM observability_events WHERE batch_id=%s AND obs_rule_id='OBS-MET-01' "
                                  "ORDER BY event_id DESC LIMIT 1", (prev,), fetch="scalar")
            if prev_val not in (None, "", "None") and int(prev_val) > 0:
                chg = (delayed - int(prev_val)) / int(prev_val)
                st = "WARN" if abs(chg) > c["metric_drift_warn"] else "OK"
                self.event("OBS-MET-01", "v_delayed_orders_governed", "delayed_order_count", delayed, prev_val, st, "warning",
                           f"延迟订单数变化 {chg:.2%}")
            else:
                self.event("OBS-MET-01", "v_delayed_orders_governed", "delayed_order_count", delayed, None, "OK", "warning",
                           "无上一批可比，记录为基准")
        except Exception as e:
            self.event("OBS-MET-01", "v_delayed_orders_governed", "delayed_order_count", None, None, "ALERT", "warning",
                       f"指标视图查询失败: {e}")
        n_alert = self.q("SELECT COUNT(*) FROM observability_events WHERE batch_id=%s AND event_status='ALERT'",
                         (self.batch_id,), fetch="scalar")
        n_warn = self.q("SELECT COUNT(*) FROM observability_events WHERE batch_id=%s AND event_status='WARN'",
                        (self.batch_id,), fetch="scalar")
        self.log_end(log_id, "success", n_alert + n_warn, None, f"ALERT={n_alert}, WARN={n_warn}")
        return n_alert, n_warn

    # ---------------- 7. 导出 ----------------
    def export(self, pipeline_status):
        q = self.q
        out = {
            "batch_id": self.batch_id, "database": self.db, "data_dir": str(self.data_dir),
            "pipeline_status": pipeline_status, "started_at": str(self.started_at), "finished_at": str(now()),
            "processing_log": [dict(zip(["log_id", "process_name", "start_time", "end_time", "input_rows", "output_rows",
                                         "status", "error_message"], map(lambda v: v if isinstance(v, (int, type(None))) else str(v), r)))
                               for r in q("SELECT log_id, process_name, start_time, end_time, input_rows, output_rows, status, "
                                          "error_message FROM processing_log WHERE batch_id=%s ORDER BY log_id", (self.batch_id,))],
            "reconciliation": [dict(zip(["table", "source_rows", "staged_rows", "quarantined_rows", "core_rows",
                                         "expected_core_rows", "status", "note"], r))
                               for r in q("SELECT table_name, source_rows, staged_rows, quarantined_rows, core_rows, "
                                          "expected_core_rows, recon_status, note FROM batch_row_reconciliation WHERE batch_id=%s",
                                          (self.batch_id,))],
            "quality": [dict(zip(["rule_id", "table", "checked", "failed", "fail_rate", "threshold", "status", "severity",
                                  "action", "samples"], [r[0], r[1], r[2], r[3], float(r[4]), float(r[5]), r[6], r[7], r[8],
                                                         json.loads(r[9] or "[]")]))
                        for r in q("SELECT rule_id, table_name, checked_rows, failed_rows, fail_rate, threshold_rate, "
                                   "check_status, severity, disposal_action, sample_keys FROM quality_check_summary "
                                   "WHERE batch_id=%s ORDER BY summary_id", (self.batch_id,))],
            "quarantine_by_rule": dict(q("SELECT rule_id, COUNT(*) FROM data_quarantine WHERE batch_id=%s GROUP BY rule_id",
                                         (self.batch_id,))),
            "flags_by_rule": dict(q("SELECT rule_id, COUNT(*) FROM data_quality_flags WHERE batch_id=%s GROUP BY rule_id",
                                    (self.batch_id,))),
            "observability": [dict(zip(["obs_rule_id", "object", "metric", "observed", "expected", "status", "message"], r))
                              for r in q("SELECT obs_rule_id, object_name, metric_name, observed_value, expected_value, "
                                         "event_status, message FROM observability_events WHERE batch_id=%s ORDER BY event_id",
                                         (self.batch_id,))],
        }
        path = self.evidence_dir / f"run_{self.batch_id}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        ol = self.openlineage_events(pipeline_status)
        ol_path = self.evidence_dir / f"openlineage_{self.batch_id}.json"
        ol_path.write_text(json.dumps(ol, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"[export] {path}\n[export] {ol_path}")

    def openlineage_events(self, pipeline_status):
        """导出 OpenLineage 风格的本地原型事件；未做完整schema校验、未连接接收端。
        自定义 batch facet 的 schemaURL 是占位值，不能视为标准合规认证或直接可部署产物。
        """
        producer = "https://github.com/INT6164/ecommerce-fulfillment/governance_pipeline"
        schema_url = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"
        ns_db = f"mysql://{self.cfg['host']}:{self.cfg['port']}"
        ns_file = "file://" + str(self.data_dir).replace("\\", "/")
        state = {"success": "COMPLETE", "partial": "COMPLETE", "failed": "FAIL"}[pipeline_status]
        run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, self.batch_id))
        recon = {r[0]: r for r in self.q("SELECT table_name, source_rows, staged_rows, core_rows FROM batch_row_reconciliation "
                                          "WHERE batch_id=%s", (self.batch_id,))}
        qmap = {}
        for rule_id, table, failed, status in self.q("SELECT rule_id, table_name, failed_rows, check_status FROM quality_check_summary "
                                                     "WHERE batch_id=%s", (self.batch_id,)):
            qmap.setdefault(table, []).append({"name": rule_id, "success": status in ("PASS", "WARN"), "failedRows": failed})
        inputs, outputs = [], []
        for t, (fname, cols) in SOURCES.items():
            r = recon.get(t)
            inputs.append({"namespace": ns_file, "name": fname, "facets": {
                "schema": {"_producer": producer,
                           "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/SchemaDatasetFacet.json",
                           "fields": [{"name": c, "type": "STRING"} for c in cols]}},
                "inputFacets": {"dataQualityMetrics": {
                    "_producer": producer,
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-2/DataQualityMetricsInputDatasetFacet.json",
                    "rowCount": r[1] if r else None}}})
            if t in CORE_ORDER:
                outputs.append({"namespace": ns_db, "name": f"{self.db}.{t}", "facets": {
                    "dataQualityAssertions": {
                        "_producer": producer,
                        "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/DataQualityAssertionsDatasetFacet.json",
                        "assertions": [{"assertion": a["name"], "success": a["success"]} for a in qmap.get(t, [])]}},
                    "outputFacets": {"outputStatistics": {
                        "_producer": producer,
                        "_schemaURL": "https://openlineage.io/spec/facets/1-0-2/OutputStatisticsOutputDatasetFacet.json",
                        "rowCount": r[3] if r else None}}})
        load_event = {
            "eventType": state, "eventTime": dt.datetime.now(dt.timezone.utc).isoformat(), "producer": producer,
            "schemaURL": schema_url,
            "run": {"runId": run_id, "facets": {"processing_engine": {
                "_producer": producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/ProcessingEngineRunFacet.json",
                "version": "MySQL 8.0", "name": "governance_pipeline.py"},
                "batch": {"_producer": producer, "_schemaURL": "https://example.local/BatchRunFacet.json",
                          "batch_id": self.batch_id, "pipeline_status": pipeline_status}}},
            "job": {"namespace": "ecommerce_fulfillment", "name": "governance_pipeline.stage_check_build"},
            "inputs": inputs, "outputs": outputs}
        metric_event = {
            "eventType": state, "eventTime": dt.datetime.now(dt.timezone.utc).isoformat(), "producer": producer,
            "schemaURL": schema_url,
            "run": {"runId": str(uuid.uuid5(uuid.NAMESPACE_URL, self.batch_id + "/delay_days")),
                    "facets": {"parent": {"_producer": producer,
                                          "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/ParentRunFacet.json",
                                          "run": {"runId": run_id},
                                          "job": {"namespace": "ecommerce_fulfillment",
                                                  "name": "governance_pipeline.stage_check_build"}}}},
            "job": {"namespace": "ecommerce_fulfillment", "name": "metric.delay_days"},
            "inputs": [{"namespace": ns_db, "name": f"{self.db}.orders"}],
            "outputs": [{"namespace": ns_db, "name": f"{self.db}.v_delayed_orders_governed", "facets": {
                "columnLineage": {
                    "_producer": producer,
                    "_schemaURL": "https://openlineage.io/spec/facets/1-2-0/ColumnLineageDatasetFacet.json",
                    "fields": {"delay_days": {"inputFields": [
                        {"namespace": ns_db, "name": f"{self.db}.orders", "field": "order_delivered_customer_date",
                         "transformations": [{"type": "DIRECT", "subtype": "TRANSFORMATION",
                                              "description": "DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)"}]},
                        {"namespace": ns_db, "name": f"{self.db}.orders", "field": "order_estimated_delivery_date",
                         "transformations": [{"type": "DIRECT", "subtype": "TRANSFORMATION",
                                              "description": "DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)"}]},
                        {"namespace": ns_db, "name": f"{self.db}.orders", "field": "order_status",
                         "transformations": [{"type": "INDIRECT", "subtype": "FILTER",
                                              "description": "order_status = 'delivered'"}]}]}}}}}]}
        return [load_event, metric_event]

    # ---------------- 主流程 ----------------
    def run(self):
        self.conn = self.connect()
        print(f"=== 批次 {self.batch_id}  数据库 {self.db}  数据目录 {self.data_dir}")
        pipe_log = self.log_start("pipeline")
        self.q("REPLACE INTO batch_data_time_profile (batch_id, process_started_at, process_status) VALUES (%s,%s,'running')",
               (self.batch_id, self.started_at), fetch=None)
        for t in SOURCES:
            self.stage_load(t)
        missing_required = [t for t in REQUIRED_SOURCES if self.step_status.get(f"stage_load.{t}") == "failed"]
        if missing_required:
            print(f"[abort] 必需源缺失或表头错误: {missing_required}，跳过检查与核心表构建（保留上一批核心数据）")
        else:
            self.run_quality_checks()
            self.cascade_quarantine()
            self.build_core()
        self.reconcile()
        biz = self.q("SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders", fetch="one")
        self.q("UPDATE batch_data_time_profile SET business_time_min=%s, business_time_max=%s WHERE batch_id=%s",
               (biz[0], biz[1], self.batch_id), fetch=None)
        n_alert, n_warn = self.evaluate_observability()
        any_failed = any(s == "failed" for s in self.step_status.values())
        status = "failed" if any_failed else ("partial" if n_alert else "success")
        self.log_end(pipe_log, status, None, None,
                     f"ALERT={n_alert}, WARN={n_warn}" + (f"; 失败步骤: {[k for k, v in self.step_status.items() if v == 'failed']}" if any_failed else ""))
        self.q("UPDATE batch_data_time_profile SET process_finished_at=%s, process_status=%s WHERE batch_id=%s",
               (now(), status, self.batch_id), fetch=None)
        self.export(status)
        print(f"=== 批次 {self.batch_id} 结束: {status}  (ALERT={n_alert}, WARN={n_warn})")
        self.conn.close()
        return self.batch_id, status


def main():
    ap = argparse.ArgumentParser(description="组员C 数据治理流水线")
    ap.add_argument("--config", default=str(HERE / "governance_config.json"))
    ap.add_argument("--database")
    ap.add_argument("--data-dir")
    ap.add_argument("--batch-prefix", default="batch")
    ap.add_argument("--init", action="store_true", help="建库并执行建表/治理/视图脚本")
    ap.add_argument("--rebuild-core", action="store_true", help="init 时强制重新执行 A 的建表脚本")
    ap.add_argument("--init-only", action="store_true")
    ap.add_argument("--no-baseline", action="store_true", help="不使用 dataREADME 基线行数（测试数据用）")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    p = Pipeline(cfg, args)
    if args.init or args.init_only:
        p.init()
        if args.init_only:
            return
        p.conn.close()
    batch_id, status = p.run()
    sys.exit(0 if status in ("success", "partial") else 2)


if __name__ == "__main__":
    main()
