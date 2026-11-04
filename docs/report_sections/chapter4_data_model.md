# 第4章 数据模型与数据库设计

## 4.1 实体与关系

### 4.1.1 核心实体

本系统围绕电商履约场景，定义了以下核心实体：

1. **订单（Order）**：记录客户的一次购买行为，包含订单状态和全生命周期时间戳（下单、批准、发货、送达、预计送达）。
2. **订单明细（Order Item）**：记录订单中的单个商品项，包含商品信息、卖家信息、价格和运费。
3. **客户（Customer）**：在平台购物的用户，包含地理位置信息。
4. **卖家（Seller）**：在平台销售商品的商家，包含地理位置信息。
5. **商品（Product）**：平台销售的物品，包含分类和物理属性。
6. **支付（Payment）**：订单的支付记录，支持多种支付方式和分期付款。
7. **评价（Review）**：客户对订单的反馈，包含评分和评论内容。
8. **地理位置（Geolocation）**：巴西邮政编码对应的经纬度坐标。

### 4.1.2 实体关系

各实体之间的关系如下：

- 一个客户可下多笔订单（Customer 1:N Order）
- 一笔订单可包含多个商品项（Order 1:N OrderItem）
- 一个商品可出现在多个订单明细中（Product 1:N OrderItem）
- 一个卖家可供应多个商品到不同订单（Seller 1:N OrderItem）
- 一笔订单可有多笔支付记录（Order 1:N OrderPayment）
- 一笔订单可有多条评价（Order 1:N Review）
- 多个客户可位于同一邮编区域（Customer N:1 Geolocation）

## 4.2 关系模式与数据字典

完整的表结构定义和数据字典详见 [数据字典文档](../data_model/data_dictionary.md)。

核心关系模式如下：

```
Customer(customer_id PK, customer_unique_id, zip_code_prefix, city, state)
Order(order_id PK, customer_id FK, status, purchase_ts, approved_at, 
      carrier_date, customer_date, estimated_date)
OrderItem(order_id FK, item_id, product_id FK, seller_id FK, 
          limit_date, price, freight, PK:(order_id, item_id))
Product(product_id PK, category_name, name_len, desc_len, photos_qty, 
        weight_g, length_cm, height_cm, width_cm)
Seller(seller_id PK, zip_prefix, city, state)
OrderPayment(order_id FK, seq, type, installments, value, PK:(order_id, seq))
Review(review_id PK, order_id FK, score, title, message, created_at, answered_at)
Geolocation(zip_prefix PK, lat, lng, city, state)
```

## 4.3 主外键及约束

### 4.3.1 主键设计

| 表名 | 主键 | 设计说明 |
|------|------|----------|
| orders | order_id (VARCHAR) | 自然键，全局唯一 |
| order_items | (order_id, order_item_id) | 联合主键 |
| customers | customer_id (VARCHAR) | 会话级客户ID |
| sellers | seller_id (VARCHAR) | 卖家ID |
| products | product_id (VARCHAR) | 商品ID |
| order_payments | (order_id, payment_sequential) | 联合主键，支持一单多支付 |
| reviews | review_id (VARCHAR) | 评价ID |
| geolocation | geolocation_zip_code_prefix (VARCHAR) | 邮编前5位 |

### 4.3.2 外键约束

| 外键 | 引用 | 级联策略 |
|------|------|----------|
| orders.customer_id | customers(customer_id) | RESTRICT |
| order_items.order_id | orders(order_id) | CASCADE |
| order_items.product_id | products(product_id) | RESTRICT |
| order_items.seller_id | sellers(seller_id) | RESTRICT |
| order_payments.order_id | orders(order_id) | CASCADE |
| reviews.order_id | orders(order_id) | CASCADE |

### 4.3.3 域约束

- order_status ∈ {'approved', 'paid', 'shipped', 'delivered', 'canceled', 'invoice_created', 'unfilled'}
- payment_type ∈ {'credit_card', 'boleto', 'debit_card', 'voucher'}
- review_score ∈ {1, 2, 3, 4, 5}
- price > 0, freight_value ≥ 0, payment_value > 0

### 4.3.4 一般化约束

- order_approved_at ≥ order_purchase_timestamp
- order_delivered_carrier_date ≥ order_approved_at
- order_delivered_customer_date ≥ order_delivered_carrier_date

完整的建表脚本见 [sql/create_tables.sql](../../sql/create_tables.sql)。

## 4.4 整合逻辑与统计粒度

### 4.4.1 避免重复计数的整合策略

**问题**：orders 与 order_items 为一对多关系，orders 与 order_payments 也为一对多关系。若将三表直接 JOIN，一笔包含 M 个商品和 N 笔支付的订单会产生 M×N 行，导致：
- 订单基本信息重复 M×N 次
- SUM(price) 被放大 N 倍
- SUM(payment_value) 被放大 M 倍

**解决方案**：采用"先聚合再连接"的策略：

```sql
-- 正确的整合方式：分别预聚合后连接
SELECT 
    o.order_id,
    item_agg.total_price,        -- 来自预聚合的order_items
    item_agg.item_count,          -- 商品数量
    payment_agg.total_payment,    -- 来自预聚合的order_payments
    payment_agg.payment_count     -- 支付笔数
FROM orders o
LEFT JOIN (
    SELECT order_id, SUM(price) AS total_price, COUNT(*) AS item_count
    FROM order_items GROUP BY order_id
) item_agg ON o.order_id = item_agg.order_id
LEFT JOIN (
    SELECT order_id, SUM(payment_value) AS total_payment, COUNT(*) AS payment_count
    FROM order_payments GROUP BY order_id
) payment_agg ON o.order_id = payment_agg.order_id;
```

此策略确保：
- 每个订单只输出 1 行
- 商品总金额 = 该订单所有商品的 price 之和
- 支付总金额 = 该订单所有支付的 payment_value 之和
- 不会出现笛卡尔积导致的金额放大

### 4.4.2 统计粒度说明

| 统计维度 | 粒度 | 说明 |
|----------|------|------|
| 订单级统计 | 每笔订单 1 行 | 使用 v_order_summary 视图 |
| 商品级统计 | 每个商品项 1 行 | 直接查询 order_items 表 |
| 支付级统计 | 每笔支付 1 行 | 直接查询 order_payments 表 |
| 客户级统计 | 每个客户 1 行 | 需对 orders 按 customer_id 聚合 |
| 卖家级统计 | 每个卖家 1 行 | 需对 order_items 按 seller_id 聚合 |

## 4.5 索引与存储策略

### 4.5.1 索引设计

| 表名 | 索引字段 | 索引类型 | 查询场景 |
|------|----------|----------|----------|
| orders | customer_id | B-tree | 按客户查询订单 |
| orders | order_status | B-tree | 按状态筛选 |
| orders | order_purchase_timestamp | B-tree | 按时间范围查询 |
| orders | (order_estimated_delivery_date, order_status) | 复合 | 延迟订单查询优化 |
| order_items | order_id | B-tree | 按订单查商品明细 |
| order_items | product_id | B-tree | 按商品查订单 |
| order_items | seller_id | B-tree | 按卖家查订单 |
| order_payments | order_id | B-tree | 按订单查支付 |
| reviews | order_id | B-tree | 按订单查评价 |

### 4.5.2 存储策略

- **字符集**：全库使用 utf8mb4，支持巴西葡萄牙语特殊字符和emoji
- **引擎**：InnoDB，支持事务和外键约束
- **数值精度**：金额字段使用 DECIMAL(10,2)，避免浮点精度问题
- **时间类型**：使用 DATETIME 而非 TIMESTAMP，避免时区问题

详细的建表脚本和索引定义见 [sql/create_tables.sql](../../sql/create_tables.sql)。

## 4.6 两项典型查询

### 4.6.1 查询1：按订单号查询履约详情

**业务需求**：客服或运营人员输入订单号，查看该订单的完整履约信息，包括订单基础信息、商品明细、支付记录和物流状态。

**SQL脚本**：见 [sql/query_order_fulfillment.sql](../../sql/query_order_fulfillment.sql)

**查询逻辑**：
1. 按 order_id 精确匹配 orders 表获取订单基础信息
2. JOIN order_items 获取商品明细（使用预聚合避免重复）
3. LEFT JOIN customers 获取客户城市/州
4. LEFT JOIN order_payments 获取支付记录
5. 同时输出汇总视图（订单总金额、商品数、支付笔数等）

**输出样例**：

| 字段 | 说明 |
|------|------|
| order_id | 订单号 |
| customer_city/state | 客户城市/州 |
| order_status | 订单状态 |
| order_purchase_timestamp | 下单时间 |
| order_delivered_customer_date | 签收时间 |
| order_estimated_delivery_date | 预计送达时间 |
| delay_days | 延迟天数（签收-预计） |
| total_items | 商品数量 |
| total_price | 商品总价 |
| total_payment | 支付总额 |
| payment_count | 支付笔数 |

### 4.6.2 查询2：按统一口径筛选延迟送达订单

**业务需求**：根据统一口径（实际送达日期 > 预计送达日期）筛选出所有延迟送达的订单，支持按时间范围筛选和统计分析。

**统一口径定义**：
- 仅统计 order_status = 'delivered' 的订单
- order_delivered_customer_date 和 order_estimated_delivery_date 均不为空
- 延迟天数 = DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)
- 延迟天数 > 0 判定为延迟送达

**SQL脚本**：见 [sql/query_delayed_orders.sql](../../sql/query_delayed_orders.sql)

**查询内容**：
1. 延迟订单列表（支持时间范围过滤，按延迟天数降序）
2. 延迟订单统计摘要（总数、平均延迟、最大延迟、总价值）
3. 按月统计延迟订单趋势
4. 按客户州统计延迟率
5. 延迟订单的商品品类分布
6. 延迟 vs 准时订单的物流时间对比

**输出样例**：

| 字段 | 说明 |
|------|------|
| order_id | 订单号 |
| delay_days | 延迟天数 |
| total_items | 商品数量 |
| total_price | 商品总价 |
| total_payment | 支付总额 |
| order_purchase_timestamp | 下单时间 |
| order_estimated_delivery_date | 预计送达时间 |
| order_delivered_customer_date | 实际签收时间 |

完整的查询验证见 [sql/verify_query_correctness.sql](../../sql/verify_query_correctness.sql) 和 [验证证据](../../evidence/query_verification_evidence.md)。
