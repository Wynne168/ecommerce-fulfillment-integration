# 安全与隐私验证记录（自动生成）

> 由 `python SRC/governance/security_verify.py` 于 2026-11-09 22:40:34 在数据库 `ecommerce_fulfillment` 实际执行生成。
> 演示账号以随机密码临时创建，验证结束后已删除；本文件不含任何密码。

## 1. 角色权限实测（应允许 / 应拒绝）

| 编号 | 账号（角色） | 操作 | 预期 | 实际 | 结论 | 数据库返回 |
|---|---|---|---|---|---|---|
| S01 | gov_cs_demo（role_cs_agent） | 客服经审计过程查询订单<br>`CALL sp_cs_lookup_order('1b3190b2dfa9d789e1f14c05b647a14a')` | 允许 | 允许 | 符合 | 成功，返回 1 行 |
| S02 | gov_cs_demo（role_cs_agent） | 客服绕过审计直接查视图<br>`SELECT * FROM v_cs_order_lookup LIMIT 1` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_cs_demo'@'localhost' for table 'v_cs_order_lookup' |
| S03 | gov_cs_demo（role_cs_agent） | 客服直接读客户表<br>`SELECT customer_unique_id FROM customers LIMIT 1` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_cs_demo'@'localhost' for table 'customers' |
| S04 | gov_cs_demo（role_cs_agent） | 客服修改订单状态<br>`UPDATE orders SET order_status='delivered' WHERE order_id='1b3190b2dfa9d789e1f14c05b647a14` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: UPDATE command denied to user 'gov_cs_demo'@'localhost' for table 'orders' |
| S05 | gov_merchant_demo（role_merchant_ops） | 商家查询本卖家明细（行级视图）<br>`SELECT COUNT(*), COUNT(DISTINCT seller_id), MIN(seller_id) FROM v_merchant_order_items` | 允许 | 允许 | 符合 | 成功，返回 1 行 |
| S06 | gov_merchant_demo（role_merchant_ops） | 商家直接读全量订单明细<br>`SELECT COUNT(*) FROM order_items` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_merchant_demo'@'localhost' for table 'order_items' |
| S07 | gov_merchant_demo（role_merchant_ops） | 商家读评价原文<br>`SELECT review_comment_message FROM reviews LIMIT 1` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_merchant_demo'@'localhost' for table 'reviews' |
| S08 | gov_manager_demo（role_platform_manager） | 管理者查看按州聚合延迟率<br>`SELECT COUNT(*), MIN(delivered_orders) FROM v_manager_delay_by_state` | 允许 | 允许 | 符合 | 成功，返回 1 行 |
| S09 | gov_manager_demo（role_platform_manager） | 管理者查看质量与观测结果<br>`SELECT COUNT(*) FROM quality_check_summary` | 允许 | 允许 | 符合 | 成功，返回 1 行 |
| S10 | gov_manager_demo（role_platform_manager） | 管理者读取客户明细<br>`SELECT * FROM customers LIMIT 1` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_manager_demo'@'localhost' for table 'customers' |
| S11 | gov_governance_demo（role_data_governance） | 治理角色只读业务表<br>`SELECT COUNT(*) FROM orders` | 允许 | 允许 | 符合 | 成功，返回 1 行 |
| S12 | gov_governance_demo（role_data_governance） | 治理角色更新隔离区处置状态<br>`UPDATE data_quarantine SET resolution_note=resolution_note WHERE quarantine_id=-1` | 允许 | 允许 | 符合 | 成功，影响 0 行 |
| S13 | gov_governance_demo（role_data_governance） | 治理角色删除业务数据<br>`DELETE FROM orders WHERE order_id='1b3190b2dfa9d789e1f14c05b647a14a'` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: DELETE command denied to user 'gov_governance_demo'@'localhost' for table 'orders' |
| S14 | gov_governance_demo（role_data_governance） | 治理角色篡改审计日志<br>`DELETE FROM access_audit_log` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: DELETE command denied to user 'gov_governance_demo'@'localhost' for table 'access_audit_log' |
| S15 | gov_etl_demo（role_etl_runner） | 运行账号写入运行记录（事务回滚）<br>`INSERT INTO processing_log (batch_id, process_name, start_time, status) VALUES ('sectest',` | 允许 | 允许 | 符合 | 成功，影响 1 行（已回滚，不留数据） |
| S16 | gov_etl_demo（role_etl_runner） | 运行账号读取审计日志<br>`SELECT * FROM access_audit_log LIMIT 1` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_etl_demo'@'localhost' for table 'access_audit_log' |
| S17 | gov_etl_demo（role_etl_runner） | 运行账号删除审计日志<br>`DELETE FROM access_audit_log` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: DELETE command denied to user 'gov_etl_demo'@'localhost' for table 'access_audit_log' |
| S18 | gov_auditor_demo（role_auditor） | 审计员读取审计日志<br>`SELECT db_user, action, record_key, result_rows FROM access_audit_log ORDER BY audit_id DE` | 允许 | 允许 | 符合 | 成功，返回 1 行 |
| S19 | gov_auditor_demo（role_auditor） | 审计员读取订单明细<br>`SELECT * FROM orders LIMIT 1` | 拒绝 | 拒绝 | 符合 | 拒绝 ERROR 1142: SELECT command denied to user 'gov_auditor_demo'@'localhost' for table 'orders' |

**19/19 个用例符合预期。**

## 2. 行级过滤与审计留痕

- 映射给 `gov_merchant_demo` 的卖家：`6560211a19b47992c3666cc44a7e94c0`；该卖家在 order_items 中真实有 2033 行。
- 商家账号经 v_merchant_order_items 查询结果（行数, 卖家数, 卖家ID）：[['2033', '1', '6560211a19b47992c3666cc44a7e94c0']]，只看到本卖家数据。
- 客服调用 `sp_cs_lookup_order('1b3190b2dfa9d789e1f14c05b647a14a')` 前后 access_audit_log 行数：1 → 2。
- 审计员读取的最新审计记录（账号, 动作, 订单, 返回行数）：[['gov_cs_demo@localhost', 'LOOKUP_ORDER', '1b3190b2dfa9d789e1f14c05b647a14a', '1']]。

审计回滚风险验证：{'query_allowed': True, 'before': 2, 'after': 2, 'issue_confirmed': True, 'detail': '成功，返回 1 行（已回滚，不留数据）'}。显式事务内CALL后ROLLBACK确实可撤销日志；因此19/19仅表示授权边界符合预期，不代表防篡改审计已实现。

## 3. 隐私扫描（真实数据）

非空评价原文 40641 条，按正则扫描结果：

| 类型 | 原文命中条数 | 脱敏视图残留条数 |
|---|---:|---:|
| 电话号码 | 2 | 0 |
| 邮箱 | 0 | 0 |
| CPF 证件号 | 0 | 0 |
| 网址 | 2 | 0 |

脱敏后样例（v_reviews_masked 输出，原文不在此展示）：

- `266d46166f2642011b1909c9d4cd779d`：comprei o produto pela cor ilustrada pelo site da loja americana, no site mostra ser preto [URL] quando o produto chegou aqui veio todos com a mesma cor, tabaco
- `75b2a12fd743171a0213b74dfa69db7d`：Aguardo o recebimento da minha encomenda com urgência...  No momento estou Insatisfeita com a empresa.  [PHONE]  [PHONE]
- `dc29a151c9cd239ec94dc30405348908`：Loja parceira de [URL] e por isso merecedora de crédito.
- `f87e60d60e2e4f3e9e761a395a73fc56`：Faltou item descrito  Me ligue [PHONE]

客户准标识符 k-匿名性（按 customer_unique_id 计，共 96096 位客户，其中 2997 位有多个 customer_id）：

比例分母为99441条客户表记录（不是跨组去重客户数）；k为组内不同customer_unique_id数。

| 准标识符组合 | 分组数 | k<5 的分组数 | 落在 k<5 分组中的记录行数 | 占记录行数比例 |
|---|---:|---:|---:|---:|
| 邮编5位 + 城市 + 州（原始） | 15034 | 8462 | 18879 | 18.99% |
| 邮编前3位 + 城市 + 州（客服视图实际口径） | 4569 | 2745 | 5359 | 5.39% |
| 邮编前3位 + 州（进一步去掉城市的设计对照） | 851 | 24 | 59 | 0.06% |
| 仅州（管理者聚合口径） | 27 | 0 | 0 | 0.00% |

按州延迟率（v_manager_delay_by_state，用于伦理分析：延迟与地域高度相关）：

| 州 | 已送达订单 | 延迟订单 | 延迟率 | 平均延迟天数 |
|---|---:|---:|---:|---:|
| AL | 397 | 85 | 21.41% | 9.54 |
| MA | 717 | 125 | 17.43% | 10.50 |
| SE | 335 | 51 | 15.22% | 16.20 |
| PI | 476 | 66 | 13.87% | 13.35 |
| CE | 1279 | 176 | 13.76% | 15.18 |
| RR | 41 | 5 | 12.20% | 36.40 |
| BA | 3256 | 396 | 12.16% | 12.02 |
| RJ | 12350 | 1495 | 12.11% | 13.52 |
| PA | 946 | 106 | 11.21% | 12.82 |
| ES | 1995 | 214 | 10.73% | 11.30 |
| PB | 517 | 54 | 10.44% | 10.33 |
| TO | 274 | 27 | 9.85% | 6.52 |
| MS | 701 | 68 | 9.70% | 8.34 |
| PE | 1593 | 153 | 9.60% | 11.97 |
| RN | 474 | 44 | 9.28% | 14.48 |
| SC | 3546 | 291 | 8.21% | 8.31 |
| GO | 1957 | 128 | 6.54% | 11.37 |
| RS | 5344 | 325 | 6.08% | 10.24 |
| MT | 886 | 53 | 5.98% | 10.64 |
| DF | 2080 | 118 | 5.67% | 7.42 |
| MG | 11354 | 519 | 4.57% | 8.40 |
| SP | 40494 | 1820 | 4.49% | 8.33 |
| PR | 4923 | 199 | 4.04% | 8.32 |
| AC | 80 | 3 | 3.75% | 18.67 |
| AP | 67 | 2 | 2.99% | 72.50 |
| RO | 243 | 7 | 2.88% | 5.57 |
| AM | 145 | 4 | 2.76% | 30.25 |

## 4. 配置与密钥核查

| 检查项 | 实际值 | 评价 |
|---|---|---|
| local_infile | OFF | 关闭，降低客户端文件读取风险 |
| secure_file_priv | C:\ProgramData\MySQL\MySQL Server 8.0\Uploads\ | 已限制服务器端导入目录 |
| require_secure_transport | OFF | 未强制 TLS，生产环境应开启 |
| have_ssl | YES | 服务器支持 TLS |
| general_log | OFF | 未开启；access_audit_log仅覆盖客服过程自动提交路径，不覆盖全库且可被事务回滚 |
| default_password_lifetime | 0 | 全局不过期；演示账号单独设置 90 天过期与登录失败锁定 |
| 审计/密码强度插件 | 无 | 社区版未安装 audit_log、validate_password |
| 项目目录 .gitignore | 不存在 | README 声称已用 .gitignore 排除密钥，实际未找到 |

项目目录（组内 MYSQL 文件夹）中发现的明文凭据（已打码）：

| 文件 | 行号 | 内容（打码） |
|---|---:|---|
| SRC\import_config.json | 2 | `mysql+pymysql://root:******@` |
| TESTS\test_config.json | 2 | `mysql+pymysql://root:******@` |

演示账号清理后剩余：无
