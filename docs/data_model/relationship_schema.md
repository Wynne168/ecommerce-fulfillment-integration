# 关系模式与建表说明

## 1. 关系模式设计原则

1. **范式化设计**：业务数据表遵循第三范式（3NF），消除传递依赖和冗余数据。
2. **系统表独立**：processing_log 和 quality_check_results 作为系统管理表，与业务数据分离。
3. **时间戳精确**：所有时间字段使用 DATETIME 类型，保留秒级精度。
4. **金额精度**：金额字段使用 DECIMAL(10,2) 避免浮点精度问题。
5. **外键约束**：所有表间关联均通过外键约束保证引用完整性。

## 2. 主键设计

| 表名 | 主键 | 设计说明 |
|------|------|----------|
| orders | order_id (VARCHAR) | 订单ID为自然键，全局唯一 |
| order_items | (order_id, order_item_id) | 联合主键，order_item_id标识订单内商品序号 |
| customers | customer_id (VARCHAR) | 会话级客户ID |
| sellers | seller_id (VARCHAR) | 卖家ID |
| products | product_id (VARCHAR) | 商品ID |
| order_payments | (order_id, payment_sequential) | 联合主键，支持一单多支付 |
| reviews | review_id (VARCHAR) | 评价ID |
| geolocation | geolocation_zip_code_prefix (VARCHAR) | 邮编前5位 |
| processing_log | log_id (INT) | 自增代理键 |
| quality_check_results | check_id (INT) | 自增代理键 |

## 3. 外键约束设计

| 外键 | 引用表(字段) | 级联策略 | 说明 |
|------|-------------|----------|------|
| orders.customer_id | customers(customer_id) | RESTRICT | 禁止删除有订单的客户 |
| order_items.order_id | orders(order_id) | CASCADE | 删除订单时同步删除明细 |
| order_items.product_id | products(product_id) | RESTRICT | 禁止删除有销售记录的商品 |
| order_items.seller_id | sellers(seller_id) | RESTRICT | 禁止删除有销售的卖家 |
| order_payments.order_id | orders(order_id) | CASCADE | 删除订单时同步删除支付记录 |
| reviews.order_id | orders(order_id) | CASCADE | 删除订单时同步删除评价 |

## 4. 可空字段策略

| 表名 | 可空字段 | 可空原因 | 默认值/处理 |
|------|----------|----------|------------|
| orders | order_status | 新订单可能尚未有状态更新 | 插入时设默认值 'approved' |
| orders | order_approved_at | 取消订单可能无批准时间 | 查询时用 COALESCE 处理 |
| orders | order_delivered_carrier_date | 未发货订单无此字段 | 延迟判断时过滤 status='delivered' |
| orders | order_delivered_customer_date | 同上 | 同上 |
| orders | order_estimated_delivery_date | 部分老数据可能缺失 | 延迟判断时过滤 IS NOT NULL |
| order_items | shipping_limit_date | 部分数据可能缺失 | 质量检查标记 |
| customers | customer_unique_id | 旧数据可能缺失 | 用 customer_id 兜底 |
| customers | customer_zip_code_prefix | 匿名订单可能缺失 | 关联 geolocation 时用 LEFT JOIN |
| products | 所有物理字段 | 卖家可能不填写 | 质量检查标记 |

## 5. 数据导入幂等性设计

为保证建表和导入脚本可重复执行（幂等），采用以下策略：

1. **建表脚本**：使用 DROP TABLE IF EXISTS 先删除已有表（注意外键依赖顺序），再创建。
2. **导入脚本**：使用 TRUNCATE TABLE 清空已有数据后再插入，或使用 INSERT IGNORE / ON CONFLICT 避免重复键冲突。
3. **批次追踪**：每次导入在 processing_log 表中记录批次信息，支持数据回滚。

## 6. 视图设计建议

### 6.1 v_order_fulfillment（订单履约详情视图）

整合订单、商品明细、支付信息的宽表，用于典型查询：

```sql
-- 逻辑定义（实际建视图见 sql/ 目录）
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    oi.product_id,
    oi.seller_id,
    oi.price,
    oi.freight_value,
    op.payment_type,
    op.payment_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN order_payments op ON o.order_id = op.order_id;
```

**注意**：此视图在一单多商品+多支付时会产生重复行，聚合查询时需使用 DISTINCT 或子查询预聚合。

### 6.2 v_order_summary（订单汇总视图）

预聚合订单级别的信息，避免每次查询都JOIN明细表：

```sql
-- 逻辑定义
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_estimated_delivery_date,
    o.order_delivered_customer_date,
    SUM(oi.price) AS total_price,
    SUM(oi.freight_value) AS total_freight,
    COUNT(oi.order_item_id) AS item_count,
    SUM(op.payment_value) AS total_payment,
    COUNT(op.payment_sequential) AS payment_count
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN order_payments op ON o.order_id = op.order_id
GROUP BY o.order_id, ...;
```

### 6.3 v_delayed_orders（延迟订单视图）

```sql
SELECT * FROM v_order_summary
WHERE order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL
  AND order_delivered_customer_date > order_estimated_delivery_date;
```
