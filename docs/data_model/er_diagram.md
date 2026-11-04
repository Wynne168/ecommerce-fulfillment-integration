# ER 图与关系模式

## 1. ER 图（实体-关系图）

### 1.1 实体

本系统包含以下核心实体：

1. **Customer（客户）**：在平台购物的用户
2. **Order（订单）**：客户的一次购买行为
3. **OrderItem（订单明细）**：订单中的单个商品项
4. **Product（商品）**：平台销售的物品
5. **Seller（卖家）**：在平台销售商品的商家
6. **Payment（支付）**：订单的支付记录
7. **Review（评价）**：客户对订单的反馈
8. **Geolocation（地理位置）**：巴西邮政编码坐标

### 1.2 实体关系图

```
┌──────────────┐       1:N       ┌──────────────┐
│  Customer    │─────────────────│   Order      │
│──────────────│                 │──────────────│
│ customer_id  │PK               │ order_id     │PK
│ unique_id    │                 │ customer_id  │FK
│ zip_prefix   │                 │ status       │
│ city         │                 │ purchase_dt  │
│ state        │                 │ approved_dt  │
└──────┬───────┘                 │ carrier_dt   │
       │                          │ customer_dt  │
       │ N:1                       │ est_delivery │
       │                          └──────┬───────┘
       │                                 │ 1:N
       │              ┌──────────────────┘
       │              │
       │        ┌─────┴──────┐       N:1     ┌──────────────┐
       │        │ OrderItem   │──────────────│  Product     │
       │        │──────────── │              │──────────────│
       │        │ order_id    │FK            │ product_id   │PK
       │        │ item_id     │              │ cat_name     │
       │        │ product_id  │FK            │ cat_name_en  │
       │        │ seller_id   │FK            │ weight_g     │
       │        │ price       │              │ length_cm    │
       │        │ freight     │              │ height_cm    │
       │        └──────┬──────┘              │ width_cm     │
       │               │ N:1                 └──────────────┘
       │               │
       │        ┌──────┴──────┐
       │        │   Seller    │
       │        │──────────── │
       │        │ seller_id   │PK
       └────────│ zip_prefix  │
                │ city        │
                │ state       │
                └─────────────┘

       ┌─────────────────────────────────────────┐
       │              Order                      │
       │              │ 1:N                       │
       │        ┌─────┴──────┐                    │
       │        │  Payment    │                    │
       │        │──────────── │                    │
       │        │ order_id    │FK                  │
       │        │ seq         │                      │
       │        │ type        │                      │
       │        │ installments│                      │
       │        │ value       │                      │
       │        └─────────────┘                    │
       │                                          │
       │        ┌─────┴──────┐                    │
       │        │  Review     │                    │
       │        │──────────── │                    │
       │        │ review_id   │PK                  │
       │        │ order_id    │FK                  │
       │        │ score       │                      │
       │        │ comment     │                      │
       │        └─────────────┘                    │
       └─────────────────────────────────────────┘
```

## 2. 关系模式（Relational Schema）

### 2.1 正式关系模式表示

```
Customer(customer_id PK, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)

Order(order_id PK, customer_id FK→Customer, order_status, order_purchase_timestamp,
      order_approved_at, order_delivered_carrier_date, order_delivered_customer_date,
      order_estimated_delivery_date)

OrderItem(order_id FK→Order, order_item_id, product_id FK→Product, seller_id FK→Seller,
          shipping_limit_date, price, freight_value,
          PK: (order_id, order_item_id))

Product(product_id PK, product_category_name, product_name_lenght, product_description_lenght,
        product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)

Seller(seller_id PK, seller_zip_code_prefix, seller_city, seller_state)

OrderPayment(order_id FK→Order, payment_sequential, payment_type, payment_installments,
             payment_value,
             PK: (order_id, payment_sequential))

Review(review_id PK, order_id FK→Order, review_score, review_comment_title,
       review_comment_message, review_creation_date, review_answer_timestamp)

Geolocation(geolocation_zip_code_prefix PK, geolocation_lat, geolocation_lng,
            geolocation_city, geolocation_state)
```

### 2.2 完整性约束

#### 域约束（Domain Constraints）
- order_status ∈ {'approved', 'paid', 'shipped', 'delivered', 'canceled', 'invoice_created', 'unfilled'}
- payment_type ∈ {'credit_card', 'boleto', 'debit_card', 'voucher'}
- review_score ∈ {1, 2, 3, 4, 5}
- payment_installments ≥ 1
- price > 0
- freight_value ≥ 0
- payment_value > 0

#### 一般化约束（Generalized Constraints）
- order_approved_at ≥ order_purchase_timestamp（批准时间不早于下单时间）
- order_delivered_carrier_date ≥ order_approved_at（发货时间不早于批准时间）
- order_delivered_customer_date ≥ order_delivered_carrier_date（签收时间不早于发货时间）
- order_delivered_customer_date ≥ order_estimated_delivery_date 时判定为延迟送达
- 同一订单的 payment_value 之和应等于订单总金额（允许浮点精度误差）

## 3. 索引策略建议

| 表名 | 索引字段 | 索引类型 | 用途 |
|------|----------|----------|------|
| orders | customer_id | B-tree | 按客户查询订单 |
| orders | order_status | B-tree | 按状态筛选订单 |
| orders | order_purchase_timestamp | B-tree | 按时间范围查询 |
| orders | (order_estimated_delivery_date, order_status) | 复合 | 延迟订单查询优化 |
| order_items | order_id | B-tree | 按订单查商品明细 |
| order_items | product_id | B-tree | 按商品查订单 |
| order_items | seller_id | B-tree | 按卖家查订单 |
| order_payments | order_id | B-tree | 按订单查支付 |
| reviews | order_id | B-tree | 按订单查评价 |
| customers | customer_unique_id | B-tree | 去重识别客户 |
