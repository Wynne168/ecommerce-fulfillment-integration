# 第2章 需求与数据分析

## 2.3 数据来源、使用条件、类型与规模

### 2.3.1 数据集来源

本项目使用的核心数据集为 **Brazilian E-Commerce Public Dataset by Olist**，由巴西知名电商平台 Olist S.A. 提供，发布在 Kaggle 数据集平台。该数据集完整记录了 2016 年 9 月至 2018 年 8 月期间，在巴西多个市场通过 Olist 平台完成的真实电商交易数据，涵盖从用户下单、支付、商家发货、物流配送到客户评价的完整履约链路。

数据集获取地址：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

### 2.3.2 数据集文件与规模

该数据集由 9 个 CSV 文件组成，包含订单、订单明细、客户、卖家、商品、支付、评价及地理位置等维度的结构化数据。各文件的规模如下表所示：

| 文件名 | 表名 | 记录数（约） | 字段数 | 说明 |
|--------|------|-------------|--------|------|
| olist_orders_dataset.csv | orders | 100,000+ | 8 | 订单主表，记录订单状态与时间戳 |
| olist_order_items_dataset.csv | order_items | 113,000+ | 7 | 订单明细表，记录每笔订单中的商品 |
| olist_customers_dataset.csv | customers | 99,400+ | 5 | 客户信息表 |
| olist_sellers_dataset.csv | sellers | 2,000+ | 4 | 卖家/商家信息表 |
| olist_products_dataset.csv | products | 31,000+ | 9 | 商品信息表 |
| olist_order_payments_dataset.csv | order_payments | 104,000+ | 5 | 订单支付记录表 |
| olist_order_reviews_dataset.csv | reviews | 100,000+ | 7 | 客户评价表 |
| olist_geolocation_dataset.csv | geolocation | 1,000,000+ | 5 | 巴西邮政编码地理坐标表 |
| product_category_name_translation.csv | - | - | 2 | 商品分类名称翻译表 |

### 2.3.3 数据类型

数据集为纯文本 CSV 格式，字段以逗号分隔，字符串字段以双引号包裹。时间戳字段采用 "YYYY-MM-DD HH:MM:SS" 格式。金额字段为浮点数。

### 2.3.4 使用条件与授权

该数据集在 Kaggle 平台发布，受 Kaggle 数据集许可协议约束。使用时需遵守以下条件：
- 仅限研究和分析用途
- 需注明数据来源
- 不得用于识别具体个人（尽管数据为公开数据集）

### 2.3.5 数据核验记录

| 核验项 | 核验结果 | 核验方法 |
|--------|----------|----------|
| 文件完整性 | 8个CSV文件均已下载 | 检查文件列表与Kaggle页面一致 |
| 字段完整性 | 各表字段与文档说明一致 | 读取CSV头部行比对 |
| 记录数量 | 与公开文档描述一致 | pandas read_csv 后 len(df) |
| 时间范围 | 2016-09 至 2018-08 | 检查时间戳字段的最小最大值 |
| 编码格式 | UTF-8 | 尝试读取无报错 |

## 2.4 各表记录粒度、关联关系与整合难点

### 2.4.1 表记录粒度说明

| 表名 | 记录粒度 | 说明 |
|------|----------|------|
| orders | 每行代表一笔订单 | 订单级维度，记录订单全生命周期时间戳 |
| order_items | 每行代表订单中的一个商品项 | 商品级维度，支持一单多商品 |
| customers | 每行代表一个客户会话 | 会话级客户标识（非用户级） |
| sellers | 每行代表一个卖家 | 卖家维度 |
| products | 每行代表一个商品SKU | 商品维度 |
| order_payments | 每行代表一笔支付记录 | 支付级维度，支持一单多支付 |
| reviews | 每行代表一条客户评价 | 评价维度 |
| geolocation | 每行代表一个邮政编码坐标 | 地理维度 |

### 2.4.2 表关联关系

核心关联关系以 orders 表为中心呈星型分布：

- orders 1:N order_items（一笔订单可含多个商品）
- orders 1:N order_payments（一笔订单可有多笔支付）
- orders 1:N reviews（一笔订单可有多条评价）
- order_items N:1 products（商品明细引用商品主数据）
- order_items N:1 sellers（商品明细引用卖家主数据）
- orders N:1 customers（订单引用客户主数据）
- customers N:1 geolocation（客户通过邮编关联地理坐标）

### 2.4.3 整合难点

**难点1：一单多商品导致重复计数**

orders 与 order_items 为一对多关系。若直接 JOIN 两表，一笔包含 3 个商品的订单会产生 3 行重复的订单信息。在进行订单级聚合（如计算订单总金额、订单数统计）时，必须先用子查询或 CTE 对 order_items 按 order_id 进行 SUM/COUNT 聚合，再与 orders 表连接。

**难点2：一单多支付导致金额放大**

orders 与 order_payments 为一对多关系。若直接 JOIN 两表，一笔包含 2 笔支付的订单会产生 2 行重复的订单信息。在计算订单总金额时，若同时 JOIN order_items 和 order_payments 两个一对多表，会产生笛卡尔积（3个商品 × 2笔支付 = 6行），导致金额被放大。正确做法是分别对两个明细表预聚合后再连接。

**难点3：取消订单缺少物流数据**

order_status 为 'canceled' 的订单可能没有 order_delivered_carrier_date、order_delivered_customer_date 等物流时间戳字段。在进行延迟分析时，必须过滤掉取消订单和未送达订单，仅对 status = 'delivered' 且相关时间戳非空的订单进行分析。

**难点4：客户标识的非唯一性**

customers 表中的 customer_id 是会话级标识，同一真实客户（customer_unique_id）可能产生多个 customer_id 记录。在进行客户级分析时，应使用 customer_unique_id 进行去重，而非 customer_id。

## 2.5 数据生命周期与访问模式

### 2.5.1 数据生命周期

该数据集的数据生命周期可分为以下几个阶段：

1. **数据采集**：Olist 平台在巴西电商交易过程中实时采集订单、支付、物流等事件数据，写入原始日志系统。
2. **数据整理**：平台运营团队对原始日志进行清洗、去重、格式标准化，生成结构化的 CSV 数据集。
3. **数据发布**：整理后的数据集以 CSV 文件形式发布在 Kaggle 平台，供研究者和数据分析人员使用。
4. **数据使用**：本项目下载数据集后，通过 ETL 流程导入关系型数据库，进行查询分析和原型开发。
5. **数据归档**：原始 CSV 文件作为源头数据永久保留，清洗后的数据库副本按批次管理，可定期重新导入。

### 2.5.2 数据访问模式

根据项目需求，数据的访问模式主要包括：

| 访问模式 | 说明 | 对应查询场景 | 频率 |
|----------|------|-------------|------|
| 点查 | 按订单号精确查询 | 客服查询某订单履约详情 | 高频 |
| 范围查询 | 按时间范围筛选订单 | 月度延迟订单统计 | 中频 |
| 聚合分析 | 按维度（州/品类/时间）聚合 | 延迟率分析、销售统计 | 中频 |
| 关联查询 | 多表JOIN获取完整信息 | 订单履约详情（含商品、支付） | 高频 |
| 质量检查 | 完整性、一致性校验 | 数据治理定期检查 | 低频 |

### 2.5.3 存储与性能考量

- **索引策略**：对 orders 表的 customer_id、order_status、order_purchase_timestamp 建立 B-tree 索引；对 order_items 的 order_id、product_id、seller_id 建立索引；对 order_payments 的 order_id 建立索引。
- **视图优化**：创建 v_order_summary 预聚合视图，避免每次查询都进行 SUM/COUNT 聚合计算。
- **数据分区**：可按 order_purchase_timestamp 的月份对 orders 表进行范围分区，加速时间范围查询。
- **缓存策略**：对于高频访问的订单详情，可在应用层实现缓存（如 Redis），减少数据库查询压力。
