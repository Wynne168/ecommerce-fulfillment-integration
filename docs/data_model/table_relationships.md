# 表关联说明

## 1. 关联关系总览

本系统共 8 张业务表和 2 张系统表，核心关联关系以 orders（订单主表）为中心，呈星型分布。

## 2. 实体关系图（文字描述）

```
                    +-------------+
                    |  customers  |
                    +-------------+
                           |
                           | 1:N
                           |
+-------------+  1:N  +----------+  1:N  +---------------+
|   orders    |------>|order_items|-----<|  products     |
+-------------+       +----------+       +---------------+
      | 1:N               | 1:N              | 1:N
      |                   |                  |
      v                   v                  v
+-------------+    +---------------+  +---------------+
|order_payments|   |   sellers     |  |  reviews      |
+-------------+    +---------------+  +---------------+
                                                |
                                                | N:1
                                                v
                                          +-------------+
                                          |geolocation|
                                          +-------------+
```

## 3. 详细关联说明

### 3.1 orders ↔ customers（一对多）

- **关系**：一个客户可有多笔订单，一笔订单属于一个客户
- **外键**：orders.customer_id → customers.customer_id
- **说明**：customer_id 是会话级ID，同一客户（customer_unique_id）可能产生多个 customer_id

### 3.2 orders ↔ order_items（一对多）

- **关系**：一笔订单可包含多个商品项，一个商品项只属于一笔订单
- **外键**：order_items.order_id → orders.order_id
- **注意**：这是"一单多商品"的根源，直接 JOIN orders 和 order_items 会导致订单信息重复

### 3.3 order_items ↔ products（一对多）

- **关系**：一个商品可出现在多个订单明细中，一个明细项只引用一个商品
- **外键**：order_items.product_id → products.product_id

### 3.4 order_items ↔ sellers（一对多）

- **关系**：一个卖家可供应多个商品到不同订单，一个明细项只来自一个卖家
- **外键**：order_items.seller_id → sellers.seller_id

### 3.5 orders ↔ order_payments（一对多）

- **关系**：一笔订单可有多笔支付记录，一笔支付只属于一笔订单
- **外键**：order_payments.order_id → orders.order_id
- **注意**：这是"多笔支付"的根源，直接 JOIN 会导致订单金额重复计算

### 3.6 orders ↔ reviews（一对多）

- **关系**：一笔订单可有多条评价（实际通常一条），一条评价只属于一笔订单
- **外键**：reviews.order_id → orders.order_id

### 3.7 customers ↔ geolocation（多对一）

- **关系**：多个客户可位于同一邮编区域，一个邮编区域对应多个客户
- **关联方式**：customers.customer_zip_code_prefix → geolocation.geolocation_zip_code_prefix

### 3.8 sellers ↔ geolocation（多对一）

- **关系**：多个卖家可位于同一邮编区域
- **关联方式**：sellers.seller_zip_code_prefix → geolocation.geolocation_zip_code_prefix

## 4. 整合难点与解决方案

### 难点1：一单多商品导致重复计数

**问题**：orders 直接 JOIN order_items 时，一笔订单若包含3个商品，订单行会重复3次。

**解决方案**：
- 方案A：先对 order_items 按 order_id 聚合（SUM(price), SUM(freight_value), COUNT(order_item_id)），再 JOIN orders
- 方案B：使用子查询或 CTE 分别聚合后再连接

### 难点2：一单多支付导致金额放大

**问题**：orders 直接 JOIN order_payments 时，一笔订单若有多笔支付，订单行重复且 payment_value 累加错误。

**解决方案**：
- 先对 order_payments 按 order_id 聚合（SUM(payment_value) AS total_payment, COUNT(*) AS payment_count），再 JOIN orders

### 难点3：多表联合时的笛卡尔积

**问题**：orders JOIN order_items JOIN order_payments 三者直接连接时，若一笔订单有3个商品和2笔支付，会产生 3×2=6 行。

**解决方案**：
- 分别对 order_items 和 order_payments 预聚合后，再与 orders 连接
- 或使用窗口函数避免重复

### 难点4：取消订单缺少物流数据

**问题**：order_status = 'canceled' 的订单可能没有 order_delivered_customer_date 等字段。

**解决方案**：
- 延迟判断仅针对 status = 'delivered' 的订单
- 查询时使用 COALESCE 处理空值
- 在质量规则中检查取消订单的完整性

### 难点5：卖家与商品的多对多

**问题**：同一商品（product_id）可能被多个卖家（seller_id）销售。

**解决方案**：
- order_items 表通过 seller_id 记录了具体由哪个卖家销售该商品
- 分析卖家绩效时应基于 order_items.seller_id 而非 products.seller_id
