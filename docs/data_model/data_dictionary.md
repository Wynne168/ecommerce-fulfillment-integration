# 数据字典

## 1. 概述

本文档定义了电商履约数据整合系统中所有数据库表的数据字典，包括表名、字段名、数据类型、字段说明、是否可空、主外键约束等信息。

## 2. 表清单

| 序号 | 表名 | 说明 | 记录粒度 |
|------|------|------|----------|
| 1 | orders | 订单主表 | 每行代表一笔订单 |
| 2 | order_items | 订单明细表 | 每行代表订单中的一个商品项 |
| 3 | customers | 客户信息表 | 每行代表一个客户 |
| 4 | sellers | 卖家信息表 | 每行代表一个卖家 |
| 5 | products | 商品信息表 | 每行代表一个商品 |
| 6 | order_payments | 订单支付表 | 每行代表一笔支付记录 |
| 7 | reviews | 客户评价表 | 每行代表一条评价 |
| 8 | geolocation | 地理位置表 | 每行代表一个邮政编码坐标 |
| 9 | processing_log | 处理日志表（系统表） | 每行代表一次数据处理批次 |
| 10 | quality_check_results | 质量检查结果表（系统表） | 每行代表一条质量检查结果 |

## 3. 表详细数据字典

### 3.1 orders（订单主表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| order_id | VARCHAR(50) | 订单唯一标识 | NO | PK |
| customer_id | VARCHAR(50) | 客户ID | NO | FK → customers.customer_id |
| order_status | VARCHAR(20) | 订单状态：approved/shipped/delivered/canceled等 | YES | |
| order_purchase_timestamp | DATETIME | 客户下单时间 | NO | |
| order_approved_at | DATETIME | 支付批准时间 | YES | |
| order_delivered_carrier_date | DATETIME | 移交物流承运商时间 | YES | |
| order_delivered_customer_date | DATETIME | 客户实际签收时间 | YES | |
| order_estimated_delivery_date | DATETIME | 预计送达日期 | YES | |

**说明**：
- 主键：order_id
- 外键：customer_id 引用 customers.customer_id
- 可空字段说明：取消的订单可能没有物流和支付相关时间戳
- 业务规则：order_approved_at >= order_purchase_timestamp；order_delivered_customer_date >= order_delivered_carrier_date

### 3.2 order_items（订单明细表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| order_id | VARCHAR(50) | 订单ID | NO | FK → orders.order_id |
| order_item_id | INT | 订单内商品序号（从1开始） | NO | |
| product_id | VARCHAR(50) | 商品ID | NO | FK → products.product_id |
| seller_id | VARCHAR(50) | 卖家ID | NO | FK → sellers.seller_id |
| shipping_limit_date | DATETIME | 卖家发货限制日期 | YES | |
| price | DECIMAL(10,2) | 商品价格 | NO | |
| freight_value | DECIMAL(10,2) | 运费（多商品时分摊） | NO | |

**说明**：
- 联合主键：(order_id, order_item_id)
- 外键：order_id 引用 orders.order_id；product_id 引用 products.product_id；seller_id 引用 sellers.seller_id
- 一个订单可包含多个商品项（order_item_id > 1）
- 运费在 multi-seller 订单中按商品比例分摊

### 3.3 customers（客户信息表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| customer_id | VARCHAR(50) | 客户ID（会话ID） | NO | PK |
| customer_unique_id | VARCHAR(50) | 客户唯一标识 | YES | |
| customer_zip_code_prefix | VARCHAR(10) | 邮编前5位 | YES | |
| customer_city | VARCHAR(50) | 城市名 | YES | |
| customer_state | VARCHAR(10) | 州代码（如SP/RJ/MG） | YES | |

**说明**：
- 主键：customer_id
- customer_unique_id 是客户的真实身份标识，同一客户可能有多条 customer_id 记录（不同设备/账号）
- 可空字段：部分旧数据可能缺少地理位置信息

### 3.4 sellers（卖家信息表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| seller_id | VARCHAR(50) | 卖家ID | NO | PK |
| seller_zip_code_prefix | VARCHAR(10) | 邮编前5位 | YES | |
| seller_city | VARCHAR(50) | 城市名 | YES | |
| seller_state | VARCHAR(10) | 州代码 | YES | |

**说明**：
- 主键：seller_id
- 一个卖家可在多个订单明细中出现

### 3.5 products（商品信息表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| product_id | VARCHAR(50) | 商品ID | NO | PK |
| product_category_name | VARCHAR(100) | 商品分类名称（葡萄牙语） | YES | |
| product_name_lenght | INT | 产品名称字符数 | YES | |
| product_description_lenght | INT | 产品描述字符数 | YES | |
| product_photos_qty | INT | 产品图片数量 | YES | |
| product_weight_g | INT | 重量（克） | YES | |
| product_length_cm | INT | 长度（厘米） | YES | |
| product_height_cm | INT | 高度（厘米） | YES | |
| product_width_cm | INT | 宽度（厘米） | YES | |

**说明**：
- 主键：product_id
- product_category_name 为葡萄牙语分类名，可关联 product_category_name_translation 表获取英文翻译
- 物理尺寸字段可能为空（部分卖家未填写）

### 3.6 order_payments（订单支付表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| order_id | VARCHAR(50) | 订单ID | NO | FK → orders.order_id |
| payment_sequential | INT | 支付笔数序号（同一订单多笔支付从1递增） | NO | |
| payment_type | VARCHAR(20) | 支付方式：credit_card/boleto/debit_card/voucher | NO | |
| payment_installments | INT | 分期期数（1=一次性付清） | NO | |
| payment_value | DECIMAL(10,2) | 该笔支付金额 | NO | |

**说明**：
- 外键：order_id 引用 orders.order_id
- 联合主键：(order_id, payment_sequential)
- 一个订单可有多条支付记录（如先刷卡再补boleto）
- 订单总金额 = SUM(payment_value) WHERE order_id = 'xxx'

### 3.7 reviews（客户评价表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| review_id | VARCHAR(50) | 评价ID | NO | PK |
| order_id | VARCHAR(50) | 订单ID | NO | FK → orders.order_id |
| review_score | INT | 评分（1-5星） | YES | |
| review_comment_title | VARCHAR(200) | 评价标题 | YES | |
| review_comment_message | TEXT | 评价内容 | YES | |
| review_creation_date | DATETIME | 评价创建时间 | YES | |
| review_answer_timestamp | DATETIME | 卖家回复时间 | YES | |

**说明**：
- 主键：review_id
- 外键：order_id 引用 orders.order_id
- 不是所有订单都有评价

### 3.8 geolocation（地理位置表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| geolocation_zip_code_prefix | VARCHAR(10) | 邮政编码前5位 | NO | PK |
| geolocation_lat | DECIMAL(10,8) | 纬度 | NO | |
| geolocation_lng | DECIMAL(11,8) | 经度 | NO | |
| geolocation_city | VARCHAR(50) | 城市名 | YES | |
| geolocation_state | VARCHAR(10) | 州代码 | YES | |

**说明**：
- 主键：geolocation_zip_code_prefix
- 可用于计算客户与卖家之间的距离

### 3.9 processing_log（处理日志表，系统表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| log_id | INT | 日志ID | NO | PK |
| batch_id | VARCHAR(50) | 批次编号 | NO | |
| process_name | VARCHAR(50) | 处理任务名称 | NO | |
| start_time | DATETIME | 开始时间 | NO | |
| end_time | DATETIME | 结束时间 | YES | |
| input_rows | INT | 输入行数 | YES | |
| output_rows | INT | 输出行数 | YES | |
| status | VARCHAR(20) | 状态：success/failed/partial | NO | |
| error_message | TEXT | 错误摘要 | YES | |

**说明**：
- 用于记录每次数据导入、清洗、质量检查的运行批次信息
- batch_id 用于关联质量检查结果

### 3.10 quality_check_results（质量检查结果表，系统表）

| 字段名 | 数据类型 | 说明 | 可空 | 键 |
|--------|----------|------|------|-----|
| check_id | INT | 检查ID | NO | PK |
| batch_id | VARCHAR(50) | 关联处理批次 | NO | |
| check_name | VARCHAR(50) | 检查规则名称 | NO | |
| table_name | VARCHAR(50) | 被检查的表名 | NO | |
| record_id | VARCHAR(50) | 异常记录ID | YES | |
| issue_type | VARCHAR(50) | 问题类型 | NO | |
| issue_description | TEXT | 问题描述 | YES | |
| severity | VARCHAR(10) | 严重程度：critical/warning/info | NO | |
| checked_at | DATETIME | 检查时间 | NO | |

**说明**：
- 用于存储数据质量检查的结果
- batch_id 关联 processing_log 中的批次
