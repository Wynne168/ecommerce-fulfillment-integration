# 来源字段及转换说明（数据血缘信息）

## 1. 概述

本文档记录了核心业务指标"延迟天数"的数据血缘，包括源文件、源字段、纳入条件、计算规则及页面展示方式。该文档供组员C（数据治理负责人）建立指标血缘使用。

## 2. 核心指标：延迟天数（Delivery Delay Days）

### 2.1 指标定义

延迟天数 = 客户实际签收日期 - 预计送达日期

当延迟天数 > 0 时，表示该订单延迟送达。

### 2.2 数据血缘

```
┌─────────────────────────────────────────────────────────────────┐
│                    指标：延迟天数                                 │
│                                                                 │
│  源文件1: olist_orders_dataset.csv                              │
│  ├─ 源字段: order_estimated_delivery_date                       │
│  │  └─ 转换规则: 直接映射 → orders.order_estimated_delivery_date│
│  │  └─ 纳入条件: IS NOT NULL                                   │
│  │                                                              │
│  源文件2: olist_orders_dataset.csv                              │
│  ├─ 源字段: order_delivered_customer_date                       │
│  │  └─ 转换规则: 直接映射 → orders.order_delivered_customer_date│
│  │  └─ 纳入条件: IS NOT NULL AND order_status = 'delivered'     │
│  │                                                              │
│  计算规则:                                                        │
│  delay_days = DATEDIFF(order_delivered_customer_date,           │
│                         order_estimated_delivery_date)           │
│                                                                 │
│  筛选条件:                                                        │
│  - order_status = 'delivered'                                   │
│  - order_delivered_customer_date IS NOT NULL                    │
│  - order_estimated_delivery_date IS NOT NULL                    │
│  - order_delivered_customer_date > order_estimated_delivery_date│
│                                                                 │
│  输出字段:                                                        │
│  - order_id                                                     │
│  - delay_days (整数，单位：天)                                   │
│  - order_estimated_delivery_date                                │
│  - order_delivered_customer_date                                │
│                                                                 │
│  展示位置:                                                        │
│  - 原型界面：延迟订单查询页面                                    │
│  - 报告图表：延迟订单统计图表                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 字段来源追踪表

| 目标字段 | 目标表 | 源文件 | 源字段 | 转换规则 | 纳入条件 |
|----------|--------|--------|--------|----------|----------|
| order_estimated_delivery_date | orders | olist_orders_dataset.csv | order_estimated_delivery_date | 直接映射，解析日期字符串 | IS NOT NULL |
| order_delivered_customer_date | orders | olist_orders_dataset.csv | order_delivered_customer_date | 直接映射，解析日期字符串 | IS NOT NULL |
| order_status | orders | olist_orders_dataset.csv | order_status | 直接映射，统一小写 | IN ('delivered', 'canceled', 'shipped') |
| order_purchase_timestamp | orders | olist_orders_dataset.csv | order_purchase_timestamp | 直接映射，解析时间戳 | IS NOT NULL |
| order_approved_at | orders | olist_orders_dataset.csv | order_approved_at | 直接映射，解析时间戳 | 保留NULL |
| order_delivered_carrier_date | orders | olist_orders_dataset.csv | order_delivered_carrier_date | 直接映射，解析时间戳 | 保留NULL |
| order_id | orders/order_items/order_payments | 对应CSV文件的order_id列 | order_id | 直接映射，去除前后空格 | IS NOT NULL |
| customer_id | orders | olist_orders_dataset.csv | customer_id | 直接映射 | IS NOT NULL |
| price | order_items | olist_order_items_dataset.csv | price | CAST AS DECIMAL(10,2) | IS NOT NULL, > 0 |
| freight_value | order_items | olist_order_items_dataset.csv | freight_value | CAST AS DECIMAL(10,2) | IS NOT NULL, >= 0 |
| payment_value | order_payments | olist_order_payments_dataset.csv | payment_value | CAST AS DECIMAL(10,2) | IS NOT NULL, > 0 |
| payment_type | order_payments | olist_order_payments_dataset.csv | payment_type | 直接映射，统一小写 | IS NOT NULL |
| product_id | order_items | olist_order_items_dataset.csv | product_id | 直接映射 | IS NOT NULL |
| seller_id | order_items | olist_order_items_dataset.csv | seller_id | 直接映射 | IS NOT NULL |

## 3. 其他核心指标血缘

### 3.1 订单总金额

```
源字段: order_items.price (多商品求和) + order_payments.payment_value (多支付求和)
计算规则: total_amount = SUM(price) FROM order_items WHERE order_id = 'xxx'
验证规则: total_amount 应等于 SUM(payment_value) FROM order_payments WHERE order_id = 'xxx'（允许±0.01误差）
```

### 3.2 履约时长（天）

```
源字段: orders.order_delivered_customer_date, orders.order_purchase_timestamp
计算规则: fulfillment_days = DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)
纳入条件: order_status = 'delivered' AND 两个时间戳均不为NULL
```

### 3.3 卖家发货时长（天）

```
源字段: orders.order_delivered_carrier_date, orders.order_approved_at
计算规则: seller_processing_days = DATEDIFF(order_delivered_carrier_date, order_approved_at)
纳入条件: order_status = 'delivered' AND 两个时间戳均不为NULL
```

## 4. 数据质量规则与指标的关系

| 质量规则 | 影响的指标 | 规则说明 |
|----------|-----------|----------|
| 重复订单ID检查 | 所有订单级指标 | 确保order_id唯一 |
| 时间顺序一致性检查 | 延迟天数、履约时长 | order_approved_at >= order_purchase_timestamp |
| 关联完整性检查 | 金额汇总 | order_items.order_id 必须存在于 orders 表中 |
| 金额非负检查 | 订单总金额 | price >= 0, payment_value >= 0 |
| 空值率检查 | 所有指标 | 关键时间戳字段空值率超过阈值时标记 |

## 5. 提供给组员的接口说明

组员B在接入原型时，可通过以下视图/查询获取数据：

1. **订单履约详情**：使用 v_order_fulfillment 视图，按 order_id 筛选
2. **延迟订单列表**：使用 v_delayed_orders 视图，支持按时间范围筛选
3. **质量检查结果**：查询 quality_check_results 表，按 batch_id 关联
4. **处理日志**：查询 processing_log 表，获取批次信息

组员C在建立血缘时，可参考本文档的字段来源追踪表，逐字段追溯至原始CSV文件的列。
