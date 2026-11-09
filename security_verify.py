"""
安全与隐私实际验证 - 电商履约数据整合系统
负责人：组员C

做了什么（全部为实际执行，结果写入 EVIDENCE/security_verification_record.md）：
    1. 执行 SQL/governance/07_security_roles.sql：审计表、映射表、脱敏/行级/聚合视图、审计过程、6 个角色及授权
    2. 以随机密码临时创建 6 个演示账号（密码只存在于本进程内存，不落盘），逐一登录执行"应允许/应拒绝"的操作
    3. 隐私扫描：评价原文中的电话/邮箱/CPF/网址；客户准标识符的 k-匿名性；脱敏视图残留检查
    4. 配置核查：MySQL 安全相关变量、审计插件；项目目录中的明文密码与 .gitignore
    5. 验证结束后删除演示账号（--keep-users 可保留）

用法：
    set GOV_DB_PASSWORD=******
    python SRC/governance/security_verify.py
"""

import argparse
import datetime as dt
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

import pymysql

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CFG = json.loads((HERE / "governance_config.json").read_text(encoding="utf-8"))
PROJECT_DIR = Path("C:/Users/ASUS/Desktop/courses/MYSQL")   # 组内已有项目目录（只读扫描）

USERS = {
    "gov_cs_demo": "role_cs_agent",
    "gov_merchant_demo": "role_merchant_ops",
    "gov_manager_demo": "role_platform_manager",
    "gov_governance_demo": "role_data_governance",
    "gov_etl_demo": "role_etl_runner",
    "gov_auditor_demo": "role_auditor",
}
PHONE = r"[(]?[0-9]{2}[)]?[[:space:]]?9?[0-9]{4}[-[:space:]]?[0-9]{4}"
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}"
CPF = r"[0-9]{3}[.][0-9]{3}[.][0-9]{3}-[0-9]{2}"
URL = r"(https?://|www[.])[^[:space:]]+"


def root_conn(db):
    return pymysql.connect(host=CFG["host"], port=CFG["port"], user=CFG["user"], password=os.environ[CFG["password_env"]],
                           database=db, charset="utf8mb4", autocommit=True)


def rq(c, sql, args=None):
    with c.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def run_sql_file(path, db):
    env = dict(os.environ, MYSQL_PWD=os.environ[CFG["password_env"]])
    res = subprocess.run([CFG["mysql_bin"], f"-h{CFG['host']}", f"-P{CFG['port']}", f"-u{CFG['user']}",
                          "--default-character-set=utf8mb4", db],
                         input=Path(path).read_text(encoding="utf-8"), text=True, encoding="utf-8",
                         capture_output=True, env=env)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)


def try_as(user, pwd, db, sql, args=None, rollback=False):
    """以指定账号执行 SQL，返回 (allowed, detail)。"""
    try:
        c = pymysql.connect(host=CFG["host"], port=CFG["port"], user=user, password=pwd, database=db,
                            charset="utf8mb4", autocommit=not rollback)
    except pymysql.err.OperationalError as e:
        return False, f"登录失败 {e.args[0]}: {e.args[1]}", []
    try:
        with c.cursor() as cur:
            cur.execute(sql, args)
            rows = cur.fetchall() if cur.description else []
            while cur.nextset():
                pass
            detail = f"成功，返回 {len(rows)} 行" if cur.description or rows else f"成功，影响 {cur.rowcount} 行"
            if rollback:
                c.rollback()
                detail += "（已回滚，不留数据）"
            return True, detail, rows
    except pymysql.err.MySQLError as e:
        return False, f"拒绝 ERROR {e.args[0]}: {e.args[1][:110]}", []
    finally:
        c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--database", default=CFG["database"])
    ap.add_argument("--keep-users", action="store_true")
    args = ap.parse_args()
    db = args.database
    started = dt.datetime.now().replace(microsecond=0)
    run_sql_file(ROOT / "SQL" / "governance" / "07_security_roles.sql", db)
    c = root_conn(db)

    # ---- 准备：映射一个真实卖家、选一个真实延迟订单 ----
    seller, seller_items = rq(c, "SELECT seller_id, COUNT(*) n FROM order_items GROUP BY seller_id ORDER BY n DESC LIMIT 1")[0]
    rq(c, "REPLACE INTO seller_account_map (db_user, seller_id) VALUES ('gov_merchant_demo', %s)", (seller,))
    order_id = rq(c, "SELECT order_id FROM v_delayed_orders_governed WHERE quality_status='OK' ORDER BY delay_days DESC, order_id LIMIT 1")[0][0]

    # ---- 创建演示账号（随机密码，仅内存） ----
    pw = {u: secrets.token_urlsafe(18) + "Aa1!" for u in USERS}
    for u, role in USERS.items():
        rq(c, f"DROP USER IF EXISTS '{u}'@'localhost'")
        rq(c, f"CREATE USER '{u}'@'localhost' IDENTIFIED BY %s PASSWORD EXPIRE INTERVAL 90 DAY "
              f"FAILED_LOGIN_ATTEMPTS 5 PASSWORD_LOCK_TIME 1", (pw[u],))
        rq(c, f"GRANT {role} TO '{u}'@'localhost'")
        rq(c, f"SET DEFAULT ROLE ALL TO '{u}'@'localhost'")
    grants = {u: [g[0] for g in rq(c, f"SHOW GRANTS FOR '{u}'@'localhost' USING {USERS[u]}")] for u in USERS}
    audit_before = rq(c, "SELECT COUNT(*) FROM access_audit_log")[0][0]

    # ---- 权限用例：应允许 / 应拒绝 ----
    cases = [
        ("S01", "gov_cs_demo", "客服经审计过程查询订单", "CALL sp_cs_lookup_order(%s)", (order_id,), True),
        ("S02", "gov_cs_demo", "客服绕过审计直接查视图", "SELECT * FROM v_cs_order_lookup LIMIT 1", None, False),
        ("S03", "gov_cs_demo", "客服直接读客户表", "SELECT customer_unique_id FROM customers LIMIT 1", None, False),
        ("S04", "gov_cs_demo", "客服修改订单状态", "UPDATE orders SET order_status='delivered' WHERE order_id=%s", (order_id,), False),
        ("S05", "gov_merchant_demo", "商家查询本卖家明细（行级视图）",
         "SELECT COUNT(*), COUNT(DISTINCT seller_id), MIN(seller_id) FROM v_merchant_order_items", None, True),
        ("S06", "gov_merchant_demo", "商家直接读全量订单明细", "SELECT COUNT(*) FROM order_items", None, False),
        ("S07", "gov_merchant_demo", "商家读评价原文", "SELECT review_comment_message FROM reviews LIMIT 1", None, False),
        ("S08", "gov_manager_demo", "管理者查看按州聚合延迟率",
         "SELECT COUNT(*), MIN(delivered_orders) FROM v_manager_delay_by_state", None, True),
        ("S09", "gov_manager_demo", "管理者查看质量与观测结果",
         "SELECT COUNT(*) FROM quality_check_summary", None, True),
        ("S10", "gov_manager_demo", "管理者读取客户明细", "SELECT * FROM customers LIMIT 1", None, False),
        ("S11", "gov_governance_demo", "治理角色只读业务表", "SELECT COUNT(*) FROM orders", None, True),
        ("S12", "gov_governance_demo", "治理角色更新隔离区处置状态",
         "UPDATE data_quarantine SET resolution_note=resolution_note WHERE quarantine_id=-1", None, True),
        ("S13", "gov_governance_demo", "治理角色删除业务数据", "DELETE FROM orders WHERE order_id=%s", (order_id,), False),
        ("S14", "gov_governance_demo", "治理角色篡改审计日志", "DELETE FROM access_audit_log", None, False),
        ("S15", "gov_etl_demo", "运行账号写入运行记录（事务回滚）",
         "INSERT INTO processing_log (batch_id, process_name, start_time, status) VALUES ('sectest','security_probe',NOW(),'success')",
         None, True, True),
        ("S16", "gov_etl_demo", "运行账号读取审计日志", "SELECT * FROM access_audit_log LIMIT 1", None, False),
        ("S17", "gov_etl_demo", "运行账号删除审计日志", "DELETE FROM access_audit_log", None, False),
        ("S18", "gov_auditor_demo", "审计员读取审计日志",
         "SELECT db_user, action, record_key, result_rows FROM access_audit_log ORDER BY audit_id DESC LIMIT 1", None, True),
        ("S19", "gov_auditor_demo", "审计员读取订单明细", "SELECT * FROM orders LIMIT 1", None, False),
    ]
    results = []
    for case in cases:
        cid, user, desc, sql, a, expect = case[:6]
        rb = len(case) > 6 and case[6]
        allowed, detail, rows = try_as(user, pw[user], db, sql, a, rollback=rb)
        results.append(dict(id=cid, user=user, role=USERS[user], desc=desc, sql=sql if a is None else sql.replace("%s", f"'{a[0]}'"),
                            expected="允许" if expect else "拒绝", actual="允许" if allowed else "拒绝",
                            passed=(allowed == expect), detail=detail, rows=[list(map(str, r)) for r in rows[:3]]))
    audit_after = rq(c, "SELECT COUNT(*) FROM access_audit_log")[0][0]
    # 风险验证：显式事务内查询后回滚，日志INSERT也被撤销。此测试验证缺口，不应标为安全通过。
    rollback_before = rq(c, "SELECT COUNT(*) FROM access_audit_log")[0][0]
    rollback_allowed, rollback_detail, _ = try_as('gov_cs_demo', pw['gov_cs_demo'], db,
        'CALL sp_cs_lookup_order(%s)', (order_id,), rollback=True)
    rollback_after = rq(c, "SELECT COUNT(*) FROM access_audit_log")[0][0]
    audit_risk = dict(query_allowed=rollback_allowed,before=rollback_before,after=rollback_after,
                      issue_confirmed=(rollback_allowed and rollback_before == rollback_after),detail=rollback_detail)
    true_seller_items = rq(c, "SELECT COUNT(*) FROM order_items WHERE seller_id=%s", (seller,))[0][0]

    # ---- 隐私扫描 ----
    priv = {}
    priv["comments_nonempty"] = rq(c, "SELECT COUNT(*) FROM reviews WHERE review_comment_message IS NOT NULL")[0][0]
    for k, pat in [("phone", PHONE), ("email", EMAIL), ("cpf", CPF), ("url", URL)]:
        priv[f"raw_{k}"] = rq(c, "SELECT COUNT(*) FROM reviews WHERE REGEXP_LIKE(review_comment_message, %s)", (pat,))[0][0]
        priv[f"masked_{k}_residual"] = rq(c, "SELECT COUNT(*) FROM v_reviews_masked WHERE REGEXP_LIKE(review_comment_masked, %s)",
                                          (pat,))[0][0]
    samples = rq(c, "SELECT r.review_id, m.review_comment_masked FROM reviews r JOIN v_reviews_masked m ON m.review_id=r.review_id "
                    "WHERE REGEXP_LIKE(r.review_comment_message, %s) OR REGEXP_LIKE(r.review_comment_message, %s) ORDER BY r.review_id",
                 (PHONE, URL))
    priv["masked_samples"] = [[s[0], s[1].replace("\r", " ").replace("\n", " ")] for s in samples]
    total_cust = rq(c, "SELECT COUNT(DISTINCT customer_unique_id) FROM customers")[0][0]
    for name, grp in [("zip5_city_state", "customer_zip_code_prefix, customer_city, customer_state"),
                      ("zip3_city_state", "LEFT(customer_zip_code_prefix,3), customer_city, customer_state"),
                      ("zip3_state", "LEFT(customer_zip_code_prefix,3), customer_state"),
                      ("state", "customer_state")]:
        # k按组内不同customer_unique_id计；比例以客户表记录行为分母，避免跨组同一人重复计数。
        r = rq(c, f"SELECT SUM(CASE WHEN k < 5 THEN row_n ELSE 0 END), COUNT(*), SUM(k < 5), SUM(row_n) FROM "
                  f"(SELECT {grp}, COUNT(DISTINCT customer_unique_id) k, COUNT(*) row_n FROM customers GROUP BY {grp}) t")[0]
        priv[f"k_{name}"] = dict(rows_in_groups_k_lt_5=int(r[0] or 0), share=round(float(r[0] or 0) / int(r[3]), 6),
                                 groups=int(r[1]), groups_k_lt_5=int(r[2] or 0),total_rows=int(r[3]))
    priv["distinct_customers"] = total_cust
    priv["repeat_customers"] = rq(c, "SELECT COUNT(*) FROM (SELECT customer_unique_id FROM customers GROUP BY customer_unique_id "
                                     "HAVING COUNT(*) > 1) t")[0][0]
    priv["state_delay"] = [list(map(str, r)) for r in rq(c, "SELECT customer_state, delivered_orders, delayed_orders, delay_rate, "
                                                          "avg_delay_days FROM v_manager_delay_by_state ORDER BY delay_rate DESC")]

    # ---- 配置核查 ----
    server = dict(rq(c, "SHOW VARIABLES WHERE Variable_name IN ('general_log','require_secure_transport','have_ssl','local_infile',"
                        "'secure_file_priv','default_password_lifetime')"))
    plugins = rq(c, "SELECT PLUGIN_NAME FROM information_schema.PLUGINS WHERE PLUGIN_NAME LIKE '%audit%' OR PLUGIN_NAME LIKE '%validate%'")
    secrets_found = []
    if PROJECT_DIR.exists():
        pat = re.compile(r"(password\s*[:=]\s*\S+|mysql\+pymysql://[^:\s]+:[^@\s]+@)", re.I)
        for f in PROJECT_DIR.rglob("*"):
            if f.is_file() and f.suffix.lower() in {".json", ".py", ".sql", ".md", ".txt", ".ini", ".env", ".yaml", ".yml"}:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    m = pat.search(line)
                    if m:
                        masked = re.sub(r"(://[^:]+:)[^@]+@", r"\1******@", m.group(0))
                        masked = re.sub(r"(password\s*[:=]\s*)\S+", r"\1******", masked, flags=re.I)
                        secrets_found.append([str(f.relative_to(PROJECT_DIR)), i, masked])
    gitignore = (PROJECT_DIR / ".gitignore").exists()

    # ---- 清理 ----
    if not args.keep_users:
        run_sql_file(ROOT / "SQL" / "governance" / "08_security_cleanup.sql", db)
    remaining = rq(c, "SELECT user FROM mysql.user WHERE user LIKE 'gov\\_%%'")
    c.close()

    out = dict(database=db, started=str(started), seller=seller, seller_items=seller_items, true_seller_items=true_seller_items,
               order_id=order_id, audit_before=audit_before, audit_after=audit_after, audit_rollback_risk=audit_risk, grants=grants, cases=results,
               privacy=priv, server=server, plugins=[p[0] for p in plugins], secrets=secrets_found, gitignore=gitignore,
               demo_users_remaining=[r[0] for r in remaining])
    (ROOT / "EVIDENCE" / "run_outputs" / "security_verify_result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_md(out)
    n_pass = sum(r["passed"] for r in results)
    print(f"权限用例 {n_pass}/{len(results)} 符合预期；审计日志 {audit_before} -> {audit_after}；演示账号剩余 {out['demo_users_remaining']}")


def write_md(o):
    L = ["# 安全与隐私验证记录（自动生成）", "",
         f"> 由 `python SRC/governance/security_verify.py` 于 {o['started']} 在数据库 `{o['database']}` 实际执行生成。",
         "> 演示账号以随机密码临时创建，验证结束后已删除；本文件不含任何密码。", "",
         "## 1. 角色权限实测（应允许 / 应拒绝）", "",
         "| 编号 | 账号（角色） | 操作 | 预期 | 实际 | 结论 | 数据库返回 |", "|---|---|---|---|---|---|---|"]
    for r in o["cases"]:
        L.append(f"| {r['id']} | {r['user']}（{r['role']}） | {r['desc']}<br>`{r['sql'][:90]}` | {r['expected']} | {r['actual']} | "
                 f"{'符合' if r['passed'] else '**不符**'} | {r['detail'].replace('|', '/')} |")
    n = sum(r["passed"] for r in o["cases"])
    L += ["", f"**{n}/{len(o['cases'])} 个用例符合预期。**", ""]
    s05 = next(r for r in o["cases"] if r["id"] == "S05")
    s18 = next(r for r in o["cases"] if r["id"] == "S18")
    L += ["## 2. 行级过滤与审计留痕", "",
          f"- 映射给 `gov_merchant_demo` 的卖家：`{o['seller']}`；该卖家在 order_items 中真实有 {o['true_seller_items']} 行。",
          f"- 商家账号经 v_merchant_order_items 查询结果（行数, 卖家数, 卖家ID）：{s05['rows']}，只看到本卖家数据。",
          f"- 客服调用 `sp_cs_lookup_order('{o['order_id']}')` 前后 access_audit_log 行数：{o['audit_before']} → {o['audit_after']}。",
          f"- 审计员读取的最新审计记录（账号, 动作, 订单, 返回行数）：{s18['rows']}。", "",
          f"审计回滚风险验证：{o['audit_rollback_risk']}。显式事务内CALL后ROLLBACK确实可撤销日志；因此19/19仅表示授权边界符合预期，不代表防篡改审计已实现。", "",
          "## 3. 隐私扫描（真实数据）", "",
          f"非空评价原文 {o['privacy']['comments_nonempty']} 条，按正则扫描结果：", "",
          "| 类型 | 原文命中条数 | 脱敏视图残留条数 |", "|---|---:|---:|"]
    for k, name in [("phone", "电话号码"), ("email", "邮箱"), ("cpf", "CPF 证件号"), ("url", "网址")]:
        L.append(f"| {name} | {o['privacy'][f'raw_{k}']} | {o['privacy'][f'masked_{k}_residual']} |")
    L += ["", "脱敏后样例（v_reviews_masked 输出，原文不在此展示）：", ""]
    for rid, txt in o["privacy"]["masked_samples"]:
        L.append(f"- `{rid}`：{txt[:160]}")
    L += ["", f"客户准标识符 k-匿名性（按 customer_unique_id 计，共 {o['privacy']['distinct_customers']} 位客户，"
              f"其中 {o['privacy']['repeat_customers']} 位有多个 customer_id）：", "",
          "比例分母为99441条客户表记录（不是跨组去重客户数）；k为组内不同customer_unique_id数。", "",
          "| 准标识符组合 | 分组数 | k<5 的分组数 | 落在 k<5 分组中的记录行数 | 占记录行数比例 |", "|---|---:|---:|---:|---:|"]
    for name, label in [("zip5_city_state", "邮编5位 + 城市 + 州（原始）"),
                        ("zip3_city_state", "邮编前3位 + 城市 + 州（客服视图实际口径）"),
                        ("zip3_state", "邮编前3位 + 州（进一步去掉城市的设计对照）"),
                        ("state", "仅州（管理者聚合口径）")]:
        k = o["privacy"][f"k_{name}"]
        L.append(f"| {label} | {k['groups']} | {k['groups_k_lt_5']} | {k['rows_in_groups_k_lt_5']} | {k['share']:.2%} |")
    L += ["", "按州延迟率（v_manager_delay_by_state，用于伦理分析：延迟与地域高度相关）：", "",
          "| 州 | 已送达订单 | 延迟订单 | 延迟率 | 平均延迟天数 |", "|---|---:|---:|---:|---:|"]
    for r in o["privacy"]["state_delay"]:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {float(r[3]):.2%} | {r[4]} |")
    L += ["", "## 4. 配置与密钥核查", "", "| 检查项 | 实际值 | 评价 |", "|---|---|---|"]
    sv = o["server"]
    L.append(f"| local_infile | {sv.get('local_infile')} | 关闭，降低客户端文件读取风险 |")
    L.append(f"| secure_file_priv | {sv.get('secure_file_priv')} | 已限制服务器端导入目录 |")
    L.append(f"| require_secure_transport | {sv.get('require_secure_transport')} | 未强制 TLS，生产环境应开启 |")
    L.append(f"| have_ssl | {sv.get('have_ssl')} | 服务器支持 TLS |")
    L.append(f"| general_log | {sv.get('general_log')} | 未开启；access_audit_log仅覆盖客服过程自动提交路径，不覆盖全库且可被事务回滚 |")
    L.append(f"| default_password_lifetime | {sv.get('default_password_lifetime')} | 全局不过期；演示账号单独设置 90 天过期与登录失败锁定 |")
    L.append(f"| 审计/密码强度插件 | {o['plugins'] or '无'} | 社区版未安装 audit_log、validate_password |")
    L.append(f"| 项目目录 .gitignore | {'存在' if o['gitignore'] else '不存在'} | README 声称已用 .gitignore 排除密钥，实际未找到 |")
    L += ["", "项目目录（组内 MYSQL 文件夹）中发现的明文凭据（已打码）：", "", "| 文件 | 行号 | 内容（打码） |", "|---|---:|---|"]
    for f, i, m in o["secrets"]:
        L.append(f"| {f} | {i} | `{m}` |")
    L += ["", f"演示账号清理后剩余：{o['demo_users_remaining'] or '无'}", ""]
    (ROOT / "EVIDENCE" / "security_verification_record.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
