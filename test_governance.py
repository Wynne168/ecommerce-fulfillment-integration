"""
治理规则验证测试 - 电商履约数据整合系统
负责人：组员C

用明确标注的测试数据（DATA/TEST，ID 前缀 TEST_GOV_）在独立测试库 ecommerce_fulfillment_govtest 中触发异常，
核对"预期结果（TESTS/governance_test_expected.json，运行前编写）"与"实际结果（数据库查询）"。

场景：
    A  完整测试数据：触发 45 条质量规则中的 36 条（另 9 条预期为 0，用于验证无误报），验证隔离/标记/修正、行数守恒、延迟天数血缘
    B  删除 products 源文件：验证运行失败被记录（OBS-RUN-01/03），失败批次不覆盖核心表
    C  orders 源文件截断为 7 行：验证行数漂移告警（OBS-ROW-03）

运行方式：
    set GOV_DB_PASSWORD=******
    python -m pytest TESTS/test_governance.py -v          # pytest 断言
    python TESTS/test_governance.py                       # 同时生成 EVIDENCE/governance_test_evidence.md
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "SRC" / "governance" / "governance_pipeline.py"
CFG = json.loads((ROOT / "SRC" / "governance" / "governance_config.json").read_text(encoding="utf-8"))
EXP = json.loads((ROOT / "TESTS" / "governance_test_expected.json").read_text(encoding="utf-8"))
TEST_DB = EXP["test_database"]
TEST_DATA = ROOT / "DATA" / "TEST"
assert TEST_DB.endswith("_govtest"), "安全保护：测试库名必须以 _govtest 结尾"

_CACHE = {}


def conn(db=TEST_DB):
    return pymysql.connect(host=CFG["host"], port=CFG["port"], user=CFG["user"],
                           password=os.environ[CFG["password_env"]], database=db, charset="utf8mb4", autocommit=True)


def q(sql, args=None, db=TEST_DB):
    c = conn(db)
    try:
        with c.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        c.close()


def run_pipeline(data_dir, extra=()):
    cmd = [sys.executable, str(PIPE), "--database", TEST_DB, "--data-dir", str(data_dir),
           "--batch-prefix", "test", "--no-baseline", *extra]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    batch = q("SELECT batch_id FROM processing_log WHERE process_name='pipeline' ORDER BY log_id DESC LIMIT 1")[0][0]
    return batch, res.returncode, res.stdout + res.stderr


def setup_all():
    """建立全新测试库并依次运行三个场景，结果缓存供各测试使用。"""
    if _CACHE:
        return _CACHE
    c = pymysql.connect(host=CFG["host"], port=CFG["port"], user=CFG["user"],
                        password=os.environ[CFG["password_env"]], charset="utf8mb4", autocommit=True)
    with c.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
    c.close()
    # 场景 A
    batch_a, rc_a, out_a = run_pipeline(TEST_DATA, ["--init", "--rebuild-core"])
    _CACHE["A"] = dict(batch=batch_a, rc=rc_a, out=out_a)
    _CACHE["snapshot_A"] = snapshot()
    # 场景 B：缺失 products 文件
    tmp_b = Path(tempfile.mkdtemp(prefix="gov_test_B_"))
    for f in TEST_DATA.glob("*.csv"):
        if f.name != "olist_products_dataset.csv":
            shutil.copy(f, tmp_b / f.name)
    batch_b, rc_b, out_b = run_pipeline(tmp_b)
    _CACHE["B"] = dict(batch=batch_b, rc=rc_b, out=out_b, data_dir=str(tmp_b))
    _CACHE["snapshot_B"] = snapshot()
    # 失败后暂存表可能已被覆盖，逐单追溯应不可用（0行）而不是错误绑定到失败批次。
    _CACHE["B"]["trace_rows_after_failure"] = q("SELECT COUNT(*) FROM v_delay_days_trace")[0][0]
    # 场景 C：orders 截断为前 7 条记录
    tmp_c = Path(tempfile.mkdtemp(prefix="gov_test_C_"))
    for f in TEST_DATA.glob("*.csv"):
        shutil.copy(f, tmp_c / f.name)
    lines = (TEST_DATA / "olist_orders_dataset.csv").read_text(encoding="utf-8").splitlines(keepends=True)
    (tmp_c / "olist_orders_dataset.csv").write_text("".join(lines[:8]), encoding="utf-8")
    batch_c, rc_c, out_c = run_pipeline(tmp_c)
    _CACHE["C"] = dict(batch=batch_c, rc=rc_c, out=out_c, data_dir=str(tmp_c))
    return _CACHE


def snapshot():
    """记录某一时刻核心表与指标视图的状态（各场景会重建核心表，因此必须在场景结束后立即快照）。"""
    return dict(
        core_rows={t: q(f"SELECT COUNT(*) FROM {t}")[0][0] for t in EXP["scenario_A_quality"]["expected_core_rows"]},
        quarantined_in_core=q("SELECT COUNT(*) FROM orders WHERE order_id IN ('TEST_GOV_O09','TEST_GOV_O14')")[0][0],
        negative_price_in_core=q("SELECT COUNT(*) FROM order_items WHERE price < 0")[0][0],
        governed=dict(q("SELECT order_id, delay_days FROM v_delayed_orders_governed")),
        o07_flags=q("SELECT flag_rules, quality_status FROM v_delayed_orders_governed WHERE order_id='TEST_GOV_O07'"),
        a_view=q("SELECT order_id, order_status, delay_days FROM v_delayed_orders ORDER BY order_id"),
        trace_o02=q("SELECT order_id, delay_days, core_delivered_customer_date, core_estimated_delivery_date, "
                    "raw_delivered_customer_date, raw_estimated_delivery_date, src_file, src_row_num, csv_line_no, batch_id "
                    "FROM v_delay_days_trace WHERE order_id='TEST_GOV_O02'"),
        geo_01001=q("SELECT geolocation_lat, geolocation_lng FROM geolocation WHERE geolocation_zip_code_prefix='01001'"),
    )


def pipeline_status(batch):
    return q("SELECT status FROM processing_log WHERE batch_id=%s AND process_name='pipeline'", (batch,))[0][0]


def actual_rule_hits(batch):
    hits = {}
    for rule_id, failed, status in q("SELECT rule_id, failed_rows, check_status FROM quality_check_summary WHERE batch_id=%s",
                                     (batch,)):
        keys = sorted({r[0] for r in q("SELECT record_id FROM quality_check_results WHERE batch_id=%s AND check_name=%s",
                                       (batch, rule_id))})
        hits[rule_id] = dict(count=failed, status=status, keys=keys)
    return hits


def events(batch, status=None):
    sql = "SELECT obs_rule_id, object_name, observed_value, expected_value, event_status, message FROM observability_events WHERE batch_id=%s"
    args = [batch]
    if status:
        sql += " AND event_status=%s"
        args.append(status)
    return q(sql + " ORDER BY event_id", args)


# =========================== pytest 测试 ===========================
def test_A_rule_counts_and_keys():
    r = setup_all()["A"]
    hits = actual_rule_hits(r["batch"])
    for rule_id, exp in EXP["scenario_A_quality"]["expected_failed_rows"].items():
        assert hits[rule_id]["count"] == exp["count"], f"{rule_id} 预期 {exp['count']} 实际 {hits[rule_id]['count']}"
        assert hits[rule_id]["keys"] == sorted(exp["keys"]), f"{rule_id} 键不符: {hits[rule_id]['keys']}"


def test_A_critical_rules_fail():
    r = setup_all()["A"]
    alerts = sorted({e[1] for e in events(r["batch"], "ALERT") if e[0] == "OBS-QUA-01"})
    assert alerts == sorted(EXP["scenario_A_quality"]["expected_observability"]["OBS-QUA-01 ALERT rules"])


def test_A_quarantine_and_core_rows():
    r = setup_all()["A"]
    snap = setup_all()["snapshot_A"]
    qb = dict(q("SELECT rule_id, COUNT(*) FROM data_quarantine WHERE batch_id=%s GROUP BY rule_id", (r["batch"],)))
    assert qb == EXP["scenario_A_quality"]["expected_quarantine_by_rule"]
    assert snap["core_rows"] == EXP["scenario_A_quality"]["expected_core_rows"]
    # 被隔离的记录不得进入核心表
    assert snap["quarantined_in_core"] == 0
    assert snap["negative_price_in_core"] == 0


def test_A_row_count_observability():
    r = setup_all()["A"]
    ev = events(r["batch"])
    row01 = {e[1]: e[4] for e in ev if e[0] == "OBS-ROW-01"}
    assert row01["sellers"] == "ALERT"
    assert all(v == "OK" for k, v in row01.items() if k != "sellers")
    assert all(e[4] == "OK" for e in ev if e[0] == "OBS-ROW-02")
    assert pipeline_status(r["batch"]) == "partial"


def test_A_lineage_delay_days():
    snap = setup_all()["snapshot_A"]
    exp = EXP["scenario_A_quality"]["expected_lineage"]
    assert snap["governed"] == exp["governed_delayed_orders"]
    assert snap["o07_flags"][0][0] == exp["TEST_GOV_O07_flag_rules"]
    assert len(snap["a_view"]) == exp["a_view_v_delayed_orders_count"]
    t = snap["trace_o02"]
    assert len(t) == 1 and (t[0][7], t[0][8], t[0][4], t[0][5]) == (2, 3, "2018-01-15 10:00:00", "2018-01-10 00:00:00")
    lat, lng = snap["geo_01001"][0]
    assert abs(float(lat) + 23.551) < 1e-6 and abs(float(lng) + 46.632) < 1e-6


def test_B_run_failure_recorded():
    r = setup_all()["B"]
    st = dict(q("SELECT process_name, status FROM processing_log WHERE batch_id=%s", (r["batch"],)))
    assert st["stage_load.products"] == "failed"
    assert st["pipeline"] == "failed"
    alerts = {(e[0], e[1]) for e in events(r["batch"], "ALERT")}
    assert ("OBS-RUN-03", "products") in alerts and ("OBS-RUN-01", "stage_load.products") in alerts
    assert q("SELECT COUNT(*) FROM quality_check_summary WHERE batch_id=%s", (r["batch"],))[0][0] == 0
    assert r["rc"] == 2
    # 失败批次不覆盖核心表：B 运行后核心表与 A 结束时一致
    assert setup_all()["snapshot_B"]["core_rows"] == setup_all()["snapshot_A"]["core_rows"]
    assert r["trace_rows_after_failure"] == 0  # 明确不可追溯，禁止错接失败批次原文


def test_C_row_drift_alert():
    r = setup_all()["C"]
    drift = {e[1]: e for e in events(r["batch"]) if e[0] == "OBS-ROW-03"}
    assert drift["orders"][4] == "ALERT" and drift["orders"][2] == "-50.00%"
    assert pipeline_status(r["batch"]) == "partial"


# =========================== 证据生成 ===========================
def write_evidence():
    res = setup_all()
    A, B, C = res["A"], res["B"], res["C"]
    hits = actual_rule_hits(A["batch"])
    lines = ["# 治理规则异常测试证据（自动生成）", "",
             "> 本文件由 `python TESTS/test_governance.py` 自动生成，数据全部来自测试库 `" + TEST_DB + "` 的实际查询结果。",
             "> 测试输入为 `DATA/TEST/` 下的【合成测试数据】，所有 ID 以 `TEST_GOV_` 开头，非真实 Olist 数据。",
             "> 预期结果见 `TESTS/governance_test_expected.json`（运行前编写）。", "",
             f"| 场景 | 批次 batch_id | 流水线退出码 | processing_log 批次状态 |", "|---|---|---|---|"]
    for k in ("A", "B", "C"):
        r = res[k]
        lines.append(f"| {k} | `{r['batch']}` | {r['rc']} | {pipeline_status(r['batch'])} |")
    lines += ["", "## 场景A：质量规则逐条核对（预期 vs 实际）", "",
              "| 规则 | 预期异常数 | 实际异常数 | 实际状态 | 预期记录键 | 实际记录键 | 结论 |", "|---|---:|---:|---|---|---|---|"]
    n_ok = 0
    exp_rules = EXP["scenario_A_quality"]["expected_failed_rows"]
    for rule_id, exp in exp_rules.items():
        act = hits.get(rule_id, dict(count=None, status="缺失", keys=[]))
        ok = act["count"] == exp["count"] and act["keys"] == sorted(exp["keys"])
        n_ok += ok
        lines.append(f"| {rule_id} | {exp['count']} | {act['count']} | {act['status']} | {', '.join(exp['keys']) or '-'} | "
                     f"{', '.join(act['keys']) or '-'} | {'一致' if ok else '**不一致**'} |")
    lines += ["", f"**小结：{n_ok}/{len(exp_rules)} 条规则的异常数与记录键与预期完全一致。**", ""]
    qb = dict(q("SELECT rule_id, COUNT(*) FROM data_quarantine WHERE batch_id=%s GROUP BY rule_id", (A["batch"],)))
    lines += ["## 场景A：处置结果", "", "| 隔离规则 | 预期隔离行数 | 实际隔离行数 |", "|---|---:|---:|"]
    for k, v in EXP["scenario_A_quality"]["expected_quarantine_by_rule"].items():
        lines.append(f"| {k} | {v} | {qb.get(k)} |")
    snapA, snapB = res["snapshot_A"], res["snapshot_B"]
    lines += ["", "| 核心表 | 预期行数 | 场景A后实际行数 | 场景B（失败批次）后行数 |", "|---|---:|---:|---:|"]
    for t, n in EXP["scenario_A_quality"]["expected_core_rows"].items():
        lines.append(f"| {t} | {n} | {snapA['core_rows'][t]} | {snapB['core_rows'][t]} |")
    lines += ["", f"被隔离订单 O09/O14 出现在核心表的行数：{snapA['quarantined_in_core']}（预期 0）；"
                  f"负价格明细出现在核心表的行数：{snapA['negative_price_in_core']}（预期 0）。"]
    lines += ["", "隔离区样例（raw_payload 保留原始行，便于复核与回放）：", "", "```"]
    for row in q("SELECT rule_id, table_name, src_row_num, record_key, reason, raw_payload FROM data_quarantine WHERE batch_id=%s "
                 "ORDER BY quarantine_id LIMIT 4", (A["batch"],)):
        lines.append(" | ".join(str(x) for x in row))
    lines += ["```", "", "行数守恒（batch_row_reconciliation）：", "",
              "| 表 | 源行数 | 暂存行数 | 隔离行数 | 核心行数 | 期望核心行数 | 状态 |", "|---|---:|---:|---:|---:|---:|---|"]
    for row in q("SELECT table_name, source_rows, staged_rows, quarantined_rows, core_rows, expected_core_rows, recon_status "
                 "FROM batch_row_reconciliation WHERE batch_id=%s", (A["batch"],)):
        lines.append("| " + " | ".join("-" if x is None else str(x) for x in row) + " |")
    lines += ["", "## 场景A：可观测性事件（非 OK）", "", "| 规则 | 对象 | 观测值 | 期望值 | 状态 | 说明 |", "|---|---|---|---|---|---|"]
    for e in events(A["batch"]):
        if e[4] != "OK":
            lines.append("| " + " | ".join(str(x) for x in e) + " |")
    lines += ["", "## 场景A：延迟天数血缘核对（场景A结束时快照）", "", "| 核对项 | 预期 | 实际 |", "|---|---|---|"]
    lines.append(f"| v_delayed_orders_governed | {EXP['scenario_A_quality']['expected_lineage']['governed_delayed_orders']} | {snapA['governed']} |")
    lines.append(f"| A 的 v_delayed_orders 行数 | 4 | {len(snapA['a_view'])} |")
    lines.append(f"| A 视图明细 | O02/O03(0天)/O04(canceled)/O07 | {snapA['a_view']} |")
    lines.append(f"| O07 质量标记 | CON-01,TIM-04 / FLAGGED | {snapA['o07_flags']} |")
    lines.append(f"| O02 逐级追溯 | 行号2 / CSV第3行 / 原始 2018-01-15 10:00:00 | {snapA['trace_o02']} |")
    lines.append(f"| DUP-08 修正（邮编 01001 平均坐标） | -23.551 / -46.632 | {snapA['geo_01001']} |")
    lines += ["", "## 场景B：源文件缺失导致运行失败", "", f"测试输入：复制 DATA/TEST 但删除 `olist_products_dataset.csv`（临时目录 `{B['data_dir']}`）。", "",
              "| 步骤 | 状态 | 错误信息 |", "|---|---|---|"]
    for row in q("SELECT process_name, status, error_message FROM processing_log WHERE batch_id=%s ORDER BY log_id", (B["batch"],)):
        lines.append(f"| {row[0]} | {row[1]} | {(row[2] or '')[:120]} |")
    lines += ["", "| 规则 | 对象 | 状态 | 说明 |", "|---|---|---|---|"]
    for e in events(B["batch"], "ALERT"):
        lines.append(f"| {e[0]} | {e[1]} | {e[4]} | {e[5][:120]} |")
    lines.append("")
    lines.append(f"失败批次的质量检查汇总行数：{q('SELECT COUNT(*) FROM quality_check_summary WHERE batch_id=%s', (B['batch'],))[0][0]}"
                 f"（预期 0，检查被跳过）；B 运行后核心表行数与场景A一致（见上方核心表对比列），失败批次没有覆盖已发布数据。")
    lines += ["", f"失败后逐单追溯视图行数：{B['trace_rows_after_failure']}（预期0）。暂存层已被本次载入覆盖，返回不可用而不是混用A核心值与B原文；历史原文仍需批次快照方案。", ""]
    lines += ["", "## 场景C：源文件截断导致行数漂移", "", "测试输入：复制 DATA/TEST，orders 只保留前 7 条记录。", "", 
              "| 规则 | 对象 | 观测值 | 期望值 | 状态 | 说明 |", "|---|---|---|---|---|---|"]
    for e in events(C["batch"]):
        if e[0] == "OBS-ROW-03" and e[1] == "orders" or (e[0] == "OBS-MET-01"):
            lines.append("| " + " | ".join(str(x) for x in e) + " |")
    lines += ["", "## 原始控制台输出（场景A，节选）", "", "```", *A["out"].strip().splitlines()[:70], "```", ""]
    out = ROOT / "EVIDENCE" / "governance_test_evidence.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    raw = {k: dict(batch=res[k]["batch"], rc=res[k]["rc"], stdout=res[k]["out"]) for k in ("A", "B", "C")}
    (ROOT / "EVIDENCE" / "run_outputs" / "governance_test_console.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"证据已写入 {out}")


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASSED  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAILED  {name}: {e}")
    write_evidence()
    sys.exit(1 if failures else 0)
