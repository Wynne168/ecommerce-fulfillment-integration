# 治理规则异常测试证据（自动生成）

> 本文件由 `python TESTS/test_governance.py` 自动生成，数据全部来自测试库 `ecommerce_fulfillment_govtest` 的实际查询结果。
> 测试输入为 `DATA/TEST/` 下的【合成测试数据】，所有 ID 以 `TEST_GOV_` 开头，非真实 Olist 数据。
> 预期结果见 `TESTS/governance_test_expected.json`（运行前编写）。

| 场景 | 批次 batch_id | 流水线退出码 | processing_log 批次状态 |
|---|---|---|---|
| A | `test_20261109_224055` | 0 | partial |
| B | `test_20261109_224057` | 2 | failed |
| C | `test_20261109_224059` | 0 | partial |

## 场景A：质量规则逐条核对（预期 vs 实际）

| 规则 | 预期异常数 | 实际异常数 | 实际状态 | 预期记录键 | 实际记录键 | 结论 |
|---|---:|---:|---|---|---|---|
| DUP-01 | 1 | 1 | FAIL | TEST_GOV_O02 | TEST_GOV_O02 | 一致 |
| DUP-02 | 1 | 1 | FAIL | TEST_GOV_C01 | TEST_GOV_C01 | 一致 |
| DUP-03 | 1 | 1 | FAIL | TEST_GOV_O07#1 | TEST_GOV_O07#1 | 一致 |
| DUP-04 | 1 | 1 | FAIL | TEST_GOV_O13#1 | TEST_GOV_O13#1 | 一致 |
| DUP-05 | 1 | 1 | FAIL | TEST_GOV_R02 | TEST_GOV_R02 | 一致 |
| DUP-06 | 0 | 0 | PASS | - | - | 一致 |
| DUP-07 | 0 | 0 | PASS | - | - | 一致 |
| DUP-08 | 1 | 1 | WARN | 01001 | 01001 | 一致 |
| REF-01 | 1 | 1 | FAIL | TEST_GOV_O99#1 | TEST_GOV_O99#1 | 一致 |
| REF-02 | 0 | 0 | PASS | - | - | 一致 |
| REF-03 | 1 | 1 | FAIL | TEST_GOV_O10#2 | TEST_GOV_O10#2 | 一致 |
| REF-04 | 1 | 1 | FAIL | TEST_GOV_O98#1 | TEST_GOV_O98#1 | 一致 |
| REF-05 | 1 | 1 | FAIL | TEST_GOV_R04 | TEST_GOV_R04 | 一致 |
| REF-06 | 1 | 1 | FAIL | TEST_GOV_O09 | TEST_GOV_O09 | 一致 |
| REF-07 | 1 | 1 | FAIL | TEST_GOV_O12 | TEST_GOV_O12 | 一致 |
| REF-08 | 1 | 1 | FAIL | TEST_GOV_O12 | TEST_GOV_O12 | 一致 |
| REF-09 | 1 | 1 | FAIL | TEST_GOV_C09 | TEST_GOV_C09 | 一致 |
| REF-10 | 0 | 0 | PASS | - | - | 一致 |
| REF-11 | 1 | 1 | FAIL | TEST_GOV_P03 | TEST_GOV_P03 | 一致 |
| NUL-01 | 1 | 1 | FAIL | TEST_GOV_O05 | TEST_GOV_O05 | 一致 |
| NUL-02 | 0 | 0 | PASS | - | - | 一致 |
| NUL-03 | 0 | 0 | PASS | - | - | 一致 |
| NUL-04 | 1 | 1 | FAIL | TEST_GOV_O04 | TEST_GOV_O04 | 一致 |
| NUL-05 | 1 | 1 | FAIL | TEST_GOV_O13 | TEST_GOV_O13 | 一致 |
| NUL-06 | 1 | 1 | FAIL | TEST_GOV_O14 | TEST_GOV_O14 | 一致 |
| NUL-07 | 1 | 1 | FAIL | TEST_GOV_P02 | TEST_GOV_P02 | 一致 |
| TIM-01 | 0 | 0 | PASS | - | - | 一致 |
| TIM-02 | 1 | 1 | FAIL | TEST_GOV_O06 | TEST_GOV_O06 | 一致 |
| TIM-03 | 1 | 1 | FAIL | TEST_GOV_O06 | TEST_GOV_O06 | 一致 |
| TIM-04 | 1 | 1 | FAIL | TEST_GOV_O07 | TEST_GOV_O07 | 一致 |
| TIM-05 | 0 | 0 | PASS | - | - | 一致 |
| TIM-06 | 0 | 0 | PASS | - | - | 一致 |
| TIM-07 | 1 | 1 | FAIL | TEST_GOV_R05 | TEST_GOV_R05 | 一致 |
| TIM-08 | 1 | 1 | FAIL | TEST_GOV_R06 | TEST_GOV_R06 | 一致 |
| DOM-01 | 1 | 1 | FAIL | TEST_GOV_O11 | TEST_GOV_O11 | 一致 |
| DOM-02 | 1 | 1 | FAIL | TEST_GOV_O11#2 | TEST_GOV_O11#2 | 一致 |
| DOM-03 | 1 | 1 | FAIL | TEST_GOV_O11#2 | TEST_GOV_O11#2 | 一致 |
| DOM-04 | 1 | 1 | FAIL | TEST_GOV_O06#1 | TEST_GOV_O06#1 | 一致 |
| DOM-05 | 1 | 1 | FAIL | TEST_GOV_O11#2 | TEST_GOV_O11#2 | 一致 |
| DOM-06 | 1 | 1 | FAIL | TEST_GOV_R03 | TEST_GOV_R03 | 一致 |
| DOM-07 | 1 | 1 | FAIL | TEST_GOV_O10 | TEST_GOV_O10 | 一致 |
| DOM-08 | 1 | 1 | FAIL | TEST_GOV_P04 | TEST_GOV_P04 | 一致 |
| DOM-09 | 1 | 1 | FAIL | TEST_GOV_C09 | TEST_GOV_C09 | 一致 |
| CON-01 | 2 | 2 | FAIL | TEST_GOV_O07, TEST_GOV_O13 | TEST_GOV_O07, TEST_GOV_O13 | 一致 |
| CON-02 | 1 | 1 | FAIL | TEST_GOV_O03 | TEST_GOV_O03 | 一致 |

**小结：45/45 条规则的异常数与记录键与预期完全一致。**

## 场景A：处置结果

| 隔离规则 | 预期隔离行数 | 实际隔离行数 |
|---|---:|---:|
| DUP-01 | 1 | 1 |
| DUP-02 | 1 | 1 |
| DUP-03 | 1 | 1 |
| DUP-04 | 1 | 1 |
| DUP-05 | 1 | 1 |
| REF-01 | 1 | 1 |
| REF-03 | 1 | 1 |
| REF-04 | 1 | 1 |
| REF-05 | 1 | 1 |
| REF-06 | 1 | 1 |
| NUL-06 | 1 | 1 |
| DOM-05 | 1 | 1 |
| CAS-01 | 5 | 5 |

| 核心表 | 预期行数 | 场景A后实际行数 | 场景B（失败批次）后行数 |
|---|---:|---:|---:|
| customers | 10 | 10 | 10 |
| sellers | 2 | 2 | 2 |
| products | 4 | 4 | 4 |
| geolocation | 2 | 2 | 2 |
| orders | 11 | 11 | 11 |
| order_items | 10 | 10 | 10 |
| order_payments | 11 | 11 | 11 |
| reviews | 5 | 5 | 5 |

被隔离订单 O09/O14 出现在核心表的行数：0（预期 0）；负价格明细出现在核心表的行数：0（预期 0）。

隔离区样例（raw_payload 保留原始行，便于复核与回放）：

```
DUP-01 | orders | 8 | TEST_GOV_O02 | 订单号重复 | {"order_id": "TEST_GOV_O02", "src_file": "olist_orders_dataset.csv", "customer_id": "TEST_GOV_C02", "src_row_num": 8, "order_status": "delivered", "order_approved_at": "2018-01-02 10:00:00", "order_purchase_timestamp": "2018-01-02 09:00:00", "order_delivered_carrier_date": "2018-01-04 12:00:00", "order_delivered_customer_date": "2018-01-15 10:00:00", "order_estimated_delivery_date": "2018-01-10 00:00:00"}
DUP-02 | customers | 11 | TEST_GOV_C01 | 客户ID重复 | {"src_file": "olist_customers_dataset.csv", "customer_id": "TEST_GOV_C01", "src_row_num": 11, "customer_city": "sao paulo", "customer_state": "SP", "customer_unique_id": "TEST_GOV_U01", "customer_zip_code_prefix": "01001"}
DUP-03 | order_items | 8 | TEST_GOV_O07#1 | 订单明细联合主键重复 | {"price": "70.00", "order_id": "TEST_GOV_O07", "src_file": "olist_order_items_dataset.csv", "seller_id": "TEST_GOV_S01", "product_id": "TEST_GOV_P01", "src_row_num": 8, "freight_value": "7.00", "order_item_id": "1", "shipping_limit_date": "2018-01-04 00:00:00"}
DUP-04 | order_payments | 13 | TEST_GOV_O13#1 | 支付记录联合主键重复 | {"order_id": "TEST_GOV_O13", "src_file": "olist_order_payments_dataset.csv", "src_row_num": 13, "payment_type": "credit_card", "payment_value": "100.00", "payment_sequential": "1", "payment_installments": "1"}
```

行数守恒（batch_row_reconciliation）：

| 表 | 源行数 | 暂存行数 | 隔离行数 | 核心行数 | 期望核心行数 | 状态 |
|---|---:|---:|---:|---:|---:|---|
| category_translation | 1 | 1 | 0 | - | - | OK |
| customers | 11 | 11 | 1 | 10 | 10 | OK |
| geolocation | 3 | 3 | 0 | 2 | 2 | OK |
| order_items | 16 | 16 | 6 | 10 | 10 | OK |
| order_payments | 15 | 15 | 4 | 11 | 11 | OK |
| orders | 14 | 14 | 3 | 11 | 11 | OK |
| products | 4 | 4 | 0 | 4 | 4 | OK |
| reviews | 8 | 8 | 3 | 5 | 5 | OK |
| sellers | 3 | 2 | 0 | 2 | 2 | MISMATCH |

## 场景A：可观测性事件（非 OK）

| 规则 | 对象 | 观测值 | 期望值 | 状态 | 说明 |
|---|---|---|---|---|---|
| OBS-ROW-01 | sellers | 2 | 3 | ALERT | 源 3 行，暂存 2 行 |
| OBS-QUA-01 | DUP-01 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | DUP-02 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | DUP-03 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | DUP-04 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-02 | DUP-05 | 12.5000% | <=1.5000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-01 | REF-01 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | REF-03 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | REF-04 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | REF-05 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | REF-06 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-02 | REF-07 | 7.1429% | <=1.2000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | REF-08 | 7.1429% | <=0.0500% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | REF-09 | 9.0909% | <=0.5000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | REF-11 | 25.0000% | <=0.5000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | NUL-01 | 11.1111% | <=0.0150% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | NUL-04 | 20.0000% | <=0.4000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-01 | NUL-05 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-01 | NUL-06 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-02 | NUL-07 | 25.0000% | <=3.0000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | TIM-02 | 7.1429% | <=0.2500% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | TIM-03 | 7.1429% | <=2.0000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | TIM-04 | 7.1429% | <=0.0400% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | TIM-07 | 12.5000% | <=0.1500% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | TIM-08 | 12.5000% | <=0.1000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-01 | DOM-01 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-02 | DOM-02 | 6.6667% | <=0.0100% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | DOM-03 | 6.6667% | <=0.0150% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | DOM-04 | 6.6667% | <=0.0100% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-01 | DOM-05 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-02 | DOM-06 | 12.5000% | <=0.1000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-01 | DOM-07 | 1 | 0 | ALERT | 关键规则失败 1 行（已按规则隔离/标记） |
| OBS-QUA-02 | DOM-08 | 25.0000% | <=0.1000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | DOM-09 | 9.0909% | <=0.1000% | WARN | 异常率超过阈值，异常 1 行 |
| OBS-QUA-02 | CON-01 | 15.3846% | <=0.4000% | WARN | 异常率超过阈值，异常 2 行 |
| OBS-QUA-02 | CON-02 | 11.1111% | <=2.0000% | WARN | 异常率超过阈值，异常 1 行 |

## 场景A：延迟天数血缘核对（场景A结束时快照）

| 核对项 | 预期 | 实际 |
|---|---|---|
| v_delayed_orders_governed | {'TEST_GOV_O02': 5, 'TEST_GOV_O07': 2} | {'TEST_GOV_O02': 5, 'TEST_GOV_O07': 2} |
| A 的 v_delayed_orders 行数 | 4 | 4 |
| A 视图明细 | O02/O03(0天)/O04(canceled)/O07 | (('TEST_GOV_O02', 'delivered', 5), ('TEST_GOV_O03', 'delivered', 0), ('TEST_GOV_O04', 'canceled', 2), ('TEST_GOV_O07', 'delivered', 2)) |
| O07 质量标记 | CON-01,TIM-04 / FLAGGED | (('CON-01,TIM-04', 'FLAGGED'),) |
| O02 逐级追溯 | 行号2 / CSV第3行 / 原始 2018-01-15 10:00:00 | (('TEST_GOV_O02', 5, datetime.datetime(2018, 1, 15, 10, 0), datetime.datetime(2018, 1, 10, 0, 0), '2018-01-15 10:00:00', '2018-01-10 00:00:00', 'olist_orders_dataset.csv', 2, 3, 'test_20261109_224055'),) |
| DUP-08 修正（邮编 01001 平均坐标） | -23.551 / -46.632 | ((Decimal('-23.55100000'), Decimal('-46.63200000')),) |

## 场景B：源文件缺失导致运行失败

测试输入：复制 DATA/TEST 但删除 `olist_products_dataset.csv`（临时目录 `C:\Users\ASUS\AppData\Local\Temp\gov_test_B_3ngdhm2_`）。

| 步骤 | 状态 | 错误信息 |
|---|---|---|
| pipeline | failed | ALERT=8, WARN=0; 失败步骤: ['stage_load.products'] |
| stage_load.customers | success |  |
| stage_load.sellers | partial | 1 行列数不符被跳过，样例行号: [3] |
| stage_load.products | failed | 源文件不存在: C:\Users\ASUS\AppData\Local\Temp\gov_test_B_3ngdhm2_\olist_products_dataset.csv |
| stage_load.geolocation | success |  |
| stage_load.orders | success |  |
| stage_load.order_items | success |  |
| stage_load.order_payments | success |  |
| stage_load.reviews | success |  |
| stage_load.category_translation | success |  |
| reconcile | success |  |
| observability | success | ALERT=8, WARN=0 |

| 规则 | 对象 | 状态 | 说明 |
|---|---|---|---|
| OBS-RUN-01 | stage_load.products | ALERT | stage_load.products 失败: 源文件不存在: C:\Users\ASUS\AppData\Local\Temp\gov_test_B_3ngdhm2_\olist_products_dataset.csv |
| OBS-ROW-02 | customers | ALERT | 核心 10 行，期望 11 行（暂存 11 - 隔离 0） |
| OBS-ROW-02 | order_items | ALERT | 核心 10 行，期望 16 行（暂存 16 - 隔离 0） |
| OBS-ROW-02 | order_payments | ALERT | 核心 11 行，期望 15 行（暂存 15 - 隔离 0） |
| OBS-ROW-02 | orders | ALERT | 核心 11 行，期望 14 行（暂存 14 - 隔离 0） |
| OBS-RUN-03 | products | ALERT | 源文件不存在: C:\Users\ASUS\AppData\Local\Temp\gov_test_B_3ngdhm2_\olist_products_dataset.csv |
| OBS-ROW-02 | reviews | ALERT | 核心 5 行，期望 8 行（暂存 8 - 隔离 0） |
| OBS-ROW-01 | sellers | ALERT | 源 3 行，暂存 2 行 |

失败批次的质量检查汇总行数：0（预期 0，检查被跳过）；B 运行后核心表行数与场景A一致（见上方核心表对比列），失败批次没有覆盖已发布数据。

失败后逐单追溯视图行数：0（预期0）。暂存层已被本次载入覆盖，返回不可用而不是混用A核心值与B原文；历史原文仍需批次快照方案。


## 场景C：源文件截断导致行数漂移

测试输入：复制 DATA/TEST，orders 只保留前 7 条记录。

| 规则 | 对象 | 观测值 | 期望值 | 状态 | 说明 |
|---|---|---|---|---|---|
| OBS-ROW-03 | orders | -50.00% | ±5% | ALERT | 暂存 7 行，参照 14 行（上一成功批次 test_20261109_224055） |
| OBS-MET-01 | v_delayed_orders_governed | 2 | 2 | OK | 延迟订单数变化 0.00% |

## 原始控制台输出（场景A，节选）

```
[init] 已执行组员A建表脚本: C:/Users/ASUS/Desktop/courses/MYSQL/SQL/create_tables.sql.sql
[init] 已执行 01_governance_schema.sql
[init] 已执行 04_lineage_delay_days.sql
[init] 已执行 05_observability_rules.sql
=== 批次 test_20261109_224055  数据库 ecommerce_fulfillment_govtest  数据目录 C:\Users\ASUS\Documents\Qoder\2026-11-09\a849c47f\组员C_数据治理交付物\DATA\TEST
[stage] customers              source=      11 staged=      11 success
[stage] sellers                source=       3 staged=       2 partial
[stage] products               source=       4 staged=       4 success
[stage] geolocation            source=       3 staged=       3 success
[stage] orders                 source=      14 staged=      14 success
[stage] order_items            source=      16 staged=      16 success
[stage] order_payments         source=      15 staged=      15 success
[stage] reviews                source=       8 staged=       8 success
[stage] category_translation   source=       1 staged=       1 success
[check] DUP-01  FAIL  failed=      1 /       14 (7.1429%) quarantine
[check] DUP-02  FAIL  failed=      1 /       11 (9.0909%) quarantine
[check] DUP-03  FAIL  failed=      1 /       16 (6.2500%) quarantine
[check] DUP-04  FAIL  failed=      1 /       15 (6.6667%) quarantine
[check] DUP-05  FAIL  failed=      1 /        8 (12.5000%) quarantine
[check] DUP-06  PASS  failed=      0 /        4 (0.0000%) quarantine
[check] DUP-07  PASS  failed=      0 /        2 (0.0000%) quarantine
[check] DUP-08  WARN  failed=      1 /        3 (33.3333%) fix
[check] REF-01  FAIL  failed=      1 /       16 (6.2500%) quarantine
[check] REF-02  PASS  failed=      0 /       16 (0.0000%) quarantine
[check] REF-03  FAIL  failed=      1 /       16 (6.2500%) quarantine
[check] REF-04  FAIL  failed=      1 /       15 (6.6667%) quarantine
[check] REF-05  FAIL  failed=      1 /        8 (12.5000%) quarantine
[check] REF-06  FAIL  failed=      1 /       14 (7.1429%) quarantine
[check] REF-07  FAIL  failed=      1 /       14 (7.1429%) flag
[check] REF-08  FAIL  failed=      1 /       14 (7.1429%) flag
[check] REF-09  FAIL  failed=      1 /       11 (9.0909%) flag
[check] REF-10  PASS  failed=      0 /        2 (0.0000%) flag
[check] REF-11  FAIL  failed=      1 /        4 (25.0000%) flag
[check] NUL-01  FAIL  failed=      1 /        9 (11.1111%) flag
[check] NUL-02  PASS  failed=      0 /        9 (0.0000%) flag
[check] NUL-03  PASS  failed=      0 /       11 (0.0000%) flag
[check] NUL-04  FAIL  failed=      1 /        5 (20.0000%) flag
[check] NUL-05  FAIL  failed=      1 /       14 (7.1429%) flag
[check] NUL-06  FAIL  failed=      1 /       14 (7.1429%) quarantine
[check] NUL-07  FAIL  failed=      1 /        4 (25.0000%) flag
[check] TIM-01  PASS  failed=      0 /       14 (0.0000%) flag
[check] TIM-02  FAIL  failed=      1 /       14 (7.1429%) flag
[check] TIM-03  FAIL  failed=      1 /       14 (7.1429%) flag
[check] TIM-04  FAIL  failed=      1 /       14 (7.1429%) flag
[check] TIM-05  PASS  failed=      0 /       14 (0.0000%) flag
[check] TIM-06  PASS  failed=      0 /       14 (0.0000%) flag
[check] TIM-07  FAIL  failed=      1 /        8 (12.5000%) flag
[check] TIM-08  FAIL  failed=      1 /        8 (12.5000%) flag
[check] DOM-01  FAIL  failed=      1 /       14 (7.1429%) flag
[check] DOM-02  FAIL  failed=      1 /       15 (6.6667%) flag
[check] DOM-03  FAIL  failed=      1 /       15 (6.6667%) flag
[check] DOM-04  FAIL  failed=      1 /       15 (6.6667%) flag
[check] DOM-05  FAIL  failed=      1 /       16 (6.2500%) quarantine
[check] DOM-06  FAIL  failed=      1 /        8 (12.5000%) flag
[check] DOM-07  FAIL  failed=      1 /       14 (7.1429%) fix
[check] DOM-08  FAIL  failed=      1 /        4 (25.0000%) flag
[check] DOM-09  FAIL  failed=      1 /       11 (9.0909%) flag
[check] CON-01  FAIL  failed=      2 /       13 (15.3846%) flag
[check] CON-02  FAIL  failed=      1 /        9 (11.1111%) flag
[core ] customers              rows=10
[core ] sellers                rows=2
[core ] products               rows=4
[core ] geolocation            rows=2
[core ] orders                 rows=11
[core ] order_items            rows=10
[core ] order_payments         rows=11
[core ] reviews                rows=5
[export] C:\Users\ASUS\Documents\Qoder\2026-11-09\a849c47f\组员C_数据治理交付物\EVIDENCE\run_outputs\run_test_20261109_224055.json
[export] C:\Users\ASUS\Documents\Qoder\2026-11-09\a849c47f\组员C_数据治理交付物\EVIDENCE\run_outputs\openlineage_test_20261109_224055.json
=== 批次 test_20261109_224055 结束: partial  (ALERT=15, WARN=21)
```
