# 样例核对记录

## 1. 核对目标

本记录选取样例订单，将原始CSV数据与SQL查询输出进行比对，验证查询正确性。重点验证：
1. 一单多商品时，直接连接是否造成重复计数
2. 多条支付记录时，是否造成金额放大
3. 延迟订单筛选口径是否一致

## 2. 测试环境

| 项目 | 说明 |
|------|------|
| 数据库类型 | MySQL 8.0 |
| 数据版本 | Olist Brazilian E-Commerce Dataset |
| 核对日期 | 2026年11月4日 |
| 核对人 | 组员A |

## 3. 样例订单选取

从 orders 表中选取以下特征订单进行核对：

| 样例编号 | 订单号 | 特征描述 | 商品数 | 支付笔数 |
|----------|--------|----------|--------|----------|
| 样例1 | (从实际数据选取) | 单商品、单支付、已送达 | 1 | 1 |
| 样例2 | (从实际数据选取) | 多商品、单支付、已送达 | >1 | 1 |
| 样例3 | (从实际数据选取) | 单商品、多支付、已送达 | 1 | >1 |
| 样例4 | (从实际数据选取) | 多商品、多支付、已送达 | >1 | >1 |
| 样例5 | (从实际数据选取) | 已取消订单 | - | 0或1 |

> 注：实际订单号需从数据库中查询获取后填入。

## 4. 核对方法

### 4.1 一单多商品核对（样例2）

**步骤1**：从原始CSV文件直接统计该订单的商品明细：
```
使用 pandas 读取 olist_order_items_dataset.csv，筛选 order_id = 'xxx'，统计行数和小计金额
```

**步骤2**：从数据库查询该订单的商品明细：
```
SELECT order_item_id, product_id, price, freight_value
FROM order_items WHERE order_id = 'xxx'
```

**步骤3**：对比步骤1和步骤2的结果：
- 商品行数应一致
- SUM(price) 应一致
- SUM(freight_value) 应一致

**预期结果**：两种方式的统计结果完全一致

**实际结果**：（运行查询后填写）

**核对结论**：□ 通过 □ 不通过

### 4.2 一单多支付核对（样例3）

**步骤1**：从原始CSV文件直接统计该订单的支付记录：
```
使用 pandas 读取 olist_order_payments_dataset.csv，筛选 order_id = 'xxx'，统计行数和小计金额
```

**步骤2**：从数据库查询该订单的支付记录：
```
SELECT payment_sequential, payment_type, payment_value
FROM order_payments WHERE order_id = 'xxx'
```

**步骤3**：对比步骤1和步骤2的结果：
- 支付行数应一致
- SUM(payment_value) 应一致

**预期结果**：两种方式的统计结果完全一致

**实际结果**：（运行查询后填写）

**核对结论**：□ 通过 □ 不通过

### 4.3 多表联合重复计数核对（样例4）

**步骤1**：计算直接三表JOIN的行数：
```
SELECT COUNT(*) FROM orders o
JOIN order_items oi ON o.order_id = 'xxx'
JOIN order_payments op ON o.order_id = 'xxx'
```

**步骤2**：计算预聚合后的行数：
```
SELECT COUNT(*) FROM (
    SELECT DISTINCT order_id FROM orders WHERE order_id = 'xxx'
) t
```

**步骤3**：对比两种方式的金额汇总：
- 直接JOIN的 SUM(oi.price) 应等于 预聚合的 SUM(price)
- 直接JOIN的 SUM(op.payment_value) 应等于 预聚合的 SUM(payment_value)

**预期结果**：预聚合方式的金额汇总正确，直接JOIN可能产生重复行但SUM金额仍正确（因为重复的是同一订单的相同金额）

**实际结果**：（运行查询后填写）

**核对结论**：□ 通过 □ 不通过

### 4.4 延迟订单筛选口径核对

**步骤1**：手动统计延迟订单数：
```
SELECT COUNT(*) FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL
  AND order_delivered_customer_date > order_estimated_delivery_date
```

**步骤2**：通过视图统计延迟订单数：
```
SELECT COUNT(*) FROM v_delayed_orders
```

**预期结果**：两种方式的统计结果完全一致

**实际结果**：
- 手动统计：______ 条
- 视图统计：______ 条

**核对结论**：□ 通过 □ 不通过

## 5. 核对总结

| 核对项 | 预期 | 实际 | 结论 |
|--------|------|------|------|
| 样例1：单商品单支付 | 金额一致 | ____ | □通过 □不通过 |
| 样例2：多商品单支付 | 金额一致 | ____ | □通过 □不通过 |
| 样例3：单商品多支付 | 金额一致 | ____ | □通过 □不通过 |
| 样例4：多商品多支付 | 金额一致 | ____ | □通过 □不通过 |
| 样例5：取消订单 | 空值处理正确 | ____ | □通过 □不通过 |
| 延迟订单筛选口径 | 计数一致 | ____ | □通过 □不通过 |
| 孤立记录检查 | 无孤立记录 | ____ | □通过 □不通过 |

## 6. 发现的问题

| 问题编号 | 问题描述 | 严重程度 | 处理方式 |
|----------|----------|----------|----------|
| - | （运行后如有问题在此记录） | - | - |

## 7. 附件

- SQL查询脚本：sql/query_order_fulfillment.sql
- SQL延迟查询脚本：sql/query_delayed_orders.sql
- SQL验证脚本：sql/verify_query_correctness.sql
- 建表脚本：sql/create_tables.sql
