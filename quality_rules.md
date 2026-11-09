# 质量规则清单

规则版本 v1.0；共 45 条。定义责任 C，表字段语义来自 A。首次全量检查批次 `batch_20261109_223909`。

判定：0 条异常为 PASS；有异常且异常率不超过阈值为 WARN；超过阈值为 FAIL。WARN 是已知问题仍须处置，不表示没有异常。阈值来自首次画像，仅为课堂初始值，不是业务 SLA。

| 规则 | 名称/检查条件 | 表与字段 | 严重度 | 阈值 | 处置 | 指标影响 |
|---|---|---|---|---:|---|---|
| DUP-01 | 订单号重复：orders.order_id 为主键，同一 order_id 出现多行时，除首行外其余行判为重复。 | `orders` / order_id | critical | 0.0000% | quarantine | 订单数、延迟订单数被重复计数；核心表主键冲突导致导入失败 |
| DUP-02 | 客户ID重复：customers.customer_id 为主键，重复时除首行外隔离。 | `customers` / customer_id | critical | 0.0000% | quarantine | 客户维度关联放大订单行 |
| DUP-03 | 订单明细联合主键重复：(order_id, order_item_id) 为联合主键，重复时除首行外隔离。 | `order_items` / order_id, order_item_id | critical | 0.0000% | quarantine | 商品金额 SUM(price) 被放大 |
| DUP-04 | 支付记录联合主键重复：(order_id, payment_sequential) 为联合主键，重复时除首行外隔离。 | `order_payments` / order_id, payment_sequential | critical | 0.0000% | quarantine | 支付总额 SUM(payment_value) 被放大 |
| DUP-05 | 评价ID对应多个订单：A 的模型以 review_id 为主键，但源数据中同一 review_id 关联多个 order_id。为满足主键约束，除首行外隔离并保留原始负载，建议 A 将主键改为 (review_id, order_id)。 | `reviews` / review_id | warning | 1.5000% | quarantine | 被隔离的订单缺少评价，评分类指标覆盖率下降 |
| DUP-06 | 商品ID重复：products.product_id 为主键，重复时除首行外隔离。 | `products` / product_id | critical | 0.0000% | quarantine | 品类分布统计放大 |
| DUP-07 | 卖家ID重复：sellers.seller_id 为主键，重复时除首行外隔离。 | `sellers` / seller_id | critical | 0.0000% | quarantine | 卖家绩效统计放大 |
| DUP-08 | 邮编前缀多坐标：A 的模型以邮编前缀为主键，但源文件中一个前缀对应多行坐标。处置为修正：按前缀聚合，经纬度取平均值、城市/州取首行，而不是像原导入脚本那样静默保留首行。 | `geolocation` / geolocation_zip_code_prefix | info | 100.0000% | fix | 若直接关联会使客户/卖家行数膨胀 |
| REF-01 | 明细找不到订单：order_items.order_id 必须存在于 orders。 | `order_items` / order_id | critical | 0.0000% | quarantine | 孤立明细使商品金额无法归属订单，FK 约束导致导入失败 |
| REF-02 | 明细找不到商品：order_items.product_id 必须存在于 products。 | `order_items` / product_id | critical | 0.0000% | quarantine | 品类维度统计缺失 |
| REF-03 | 明细找不到卖家：order_items.seller_id 必须存在于 sellers。 | `order_items` / seller_id | critical | 0.0000% | quarantine | 卖家绩效统计缺失 |
| REF-04 | 支付找不到订单：order_payments.order_id 必须存在于 orders。 | `order_payments` / order_id | critical | 0.0000% | quarantine | 支付金额无法归属订单 |
| REF-05 | 评价找不到订单：reviews.order_id 必须存在于 orders。 | `reviews` / order_id | critical | 0.0000% | quarantine | 评价无法归属订单 |
| REF-06 | 订单找不到客户：orders.customer_id 必须存在于 customers。 | `orders` / customer_id | critical | 0.0000% | quarantine | 按州/城市的延迟率无法计算；其明细与支付级联隔离 |
| REF-07 | 订单没有任何明细：反向关联：orders 中存在但 order_items 中没有明细的订单。 | `orders` / order_id | warning | 1.2000% | flag | v_order_fulfillment 使用 INNER JOIN 会丢失这些订单；订单金额显示为 0 |
| REF-08 | 订单没有支付记录：反向关联：orders 中存在但 order_payments 中没有记录的订单。 | `orders` / order_id | warning | 0.0500% | flag | 支付总额为 0，金额核对失败 |
| REF-09 | 客户邮编无坐标：customers.customer_zip_code_prefix 在 geolocation 中找不到。 | `customers` / customer_zip_code_prefix | info | 0.5000% | flag | 距离类分析需使用 LEFT JOIN 并接受缺失 |
| REF-10 | 卖家邮编无坐标：sellers.seller_zip_code_prefix 在 geolocation 中找不到。 | `sellers` / seller_zip_code_prefix | info | 0.5000% | flag | 卖家-客户距离无法计算 |
| REF-11 | 品类无英文翻译：非空品类名在 product_category_name_translation 中找不到对应英文名。 | `products` / product_category_name | info | 0.5000% | flag | 英文品类展示为空 |
| NUL-01 | 已送达但缺签收时间：order_status = 'delivered' 时 order_delivered_customer_date 不应为空。 | `orders` / order_status, order_delivered_customer_date | warning | 0.0150% | flag | 延迟天数无法计算，被统一口径排除，延迟率分母减少 |
| NUL-02 | 已送达但缺支付批准时间：order_status = 'delivered' 时 order_approved_at 不应为空。 | `orders` / order_status, order_approved_at | warning | 0.0300% | flag | 卖家发货时长无法计算 |
| NUL-03 | 已发货/送达但缺承运时间：order_status IN ('shipped','delivered') 时 order_delivered_carrier_date 不应为空。 | `orders` / order_status, order_delivered_carrier_date | warning | 0.0100% | flag | 物流时长无法计算 |
| NUL-04 | 未送达状态却有签收时间：order_status <> 'delivered' 时出现 order_delivered_customer_date，状态与时间戳矛盾。 | `orders` / order_status, order_delivered_customer_date | warning | 0.4000% | flag | A 的 v_delayed_orders 未限定状态，会把此类订单计入延迟（7827 vs 7826 差异来源） |
| NUL-05 | 缺预计送达日期：order_estimated_delivery_date 为延迟天数的必需输入，不应为空。 | `orders` / order_estimated_delivery_date | critical | 0.0000% | flag | 延迟天数无法计算 |
| NUL-06 | 订单关键字段为空：order_id、customer_id、order_purchase_timestamp 为 NOT NULL 关键字段。 | `orders` / order_id, customer_id, order_purchase_timestamp | critical | 0.0000% | quarantine | 无法定位订单或无法按时间范围统计 |
| NUL-07 | 商品品类为空：product_category_name 为空，品类分布中归入'未知'。 | `products` / product_category_name | info | 3.0000% | flag | 延迟订单品类分布中出现'未知'品类 |
| TIM-01 | 批准早于下单：order_approved_at >= order_purchase_timestamp（A 数据字典业务规则）。 | `orders` / order_approved_at, order_purchase_timestamp | warning | 0.1000% | flag | 卖家处理时长为负 |
| TIM-02 | 交承运早于下单：order_delivered_carrier_date 不应早于 order_purchase_timestamp。 | `orders` / order_delivered_carrier_date, order_purchase_timestamp | warning | 0.2500% | flag | 物流时长、履约时长分解失真 |
| TIM-03 | 交承运早于支付批准：order_delivered_carrier_date >= order_approved_at（A 关系模式一般化约束）。 | `orders` / order_delivered_carrier_date, order_approved_at | info | 2.0000% | flag | 卖家发货时长为负，可能是批准时间回写延迟 |
| TIM-04 | 签收早于交承运：order_delivered_customer_date >= order_delivered_carrier_date（A 数据字典业务规则）。 | `orders` / order_delivered_customer_date, order_delivered_carrier_date | warning | 0.0400% | flag | 签收时间可疑，相关订单的延迟天数可信度降低（页面以标记提示） |
| TIM-05 | 签收早于下单：order_delivered_customer_date 不得早于 order_purchase_timestamp。 | `orders` / order_delivered_customer_date, order_purchase_timestamp | critical | 0.0000% | flag | 履约时长为负，延迟天数不可信 |
| TIM-06 | 预计送达早于下单：order_estimated_delivery_date 不得早于 order_purchase_timestamp。 | `orders` / order_estimated_delivery_date, order_purchase_timestamp | critical | 0.0000% | flag | 延迟天数被系统性放大 |
| TIM-07 | 评价早于下单：review_creation_date 不应早于对应订单的下单时间。 | `reviews` / review_creation_date, orders.order_purchase_timestamp | info | 0.1500% | flag | 评价与订单关联可疑 |
| TIM-08 | 回复早于评价：review_answer_timestamp 不应早于 review_creation_date。 | `reviews` / review_answer_timestamp, review_creation_date | warning | 0.1000% | flag | 回复时长为负 |
| DOM-01 | 订单状态不在域内：order_status 取值应属于实际业务域 ('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved')（已按源数据修订 A 的域约束）。 | `orders` / order_status | critical | 0.0000% | flag | 按状态筛选（如 delivered）的指标漏算 |
| DOM-02 | 支付方式不在域内：payment_type 应属于 ('credit_card','boleto','voucher','debit_card')。 | `order_payments` / payment_type | warning | 0.0100% | flag | 支付方式分布出现未定义类别 |
| DOM-03 | 支付金额非正：payment_value > 0（A 域约束）；无法解析为数字也视为异常。 | `order_payments` / payment_value | warning | 0.0150% | flag | 支付总额与商品金额核对失败 |
| DOM-04 | 分期数小于1：payment_installments >= 1（A 域约束）。 | `order_payments` / payment_installments | warning | 0.0100% | flag | 分期分析出现 0 期 |
| DOM-05 | 商品价格/运费非法：price > 0 且 freight_value >= 0，且均可解析为数字（核心表为 NOT NULL DECIMAL）。 | `order_items` / price, freight_value | critical | 0.0000% | quarantine | 订单金额错误，无法写入 NOT NULL 金额字段 |
| DOM-06 | 评分不在1-5：review_score ∈ {1,2,3,4,5}。 | `reviews` / review_score | warning | 0.1000% | flag | 平均评分失真 |
| DOM-07 | 订单时间戳无法解析：非空时间戳必须符合 'YYYY-MM-DD HH:MM:SS' 且为合法日期；否则修正为 NULL 并标记，避免像 pandas errors='coerce' 那样静默变成空值。 | `orders` / order_purchase_timestamp ... order_estimated_delivery_date | critical | 0.0000% | fix | 延迟天数等时间指标静默缺失 |
| DOM-08 | 商品重量/尺寸非正：非空的重量与尺寸应 > 0。 | `products` / product_weight_g, product_length_cm, product_height_cm, product_width_cm | info | 0.1000% | flag | 运费/体积分析异常 |
| DOM-09 | 州代码格式错误：customer_state 应为两位大写字母（如 SP、RJ）。 | `customers` / customer_state | warning | 0.1000% | flag | 按州延迟率统计出现异常分组 |
| CON-01 | 支付总额与商品+运费不符：同一订单 /SUM(payment_value) - SUM(price + freight_value)/ > 1.00 视为金额不一致（分期利息、优惠券可造成小额差异，故容差取 1.00）。 | `orders` / SUM(payment_value) vs SUM(price+freight_value) | warning | 0.4000% | flag | 订单金额展示与支付对账不一致 |
| CON-02 | 晚于预计时刻但延迟天数为0：已送达订单签收时间 > 预计送达时间（预计时间均为 00:00:00），但 DATEDIFF = 0（当天签收）。'实际 > 预计' 与 '延迟天数 > 0' 两种口径对这些订单结论相反，需组长确认统一口径。 | `orders` / order_delivered_customer_date, order_estimated_delivery_date | info | 2.0000% | flag | 延迟订单数在 7826（时刻口径）与 6534（天数口径）之间摇摆 |

## 分母与可执行条件

| 编号 | 分母查询 |
|---|---|
| DUP-01 | `SELECT COUNT(*) FROM stg_orders` |
| DUP-02 | `SELECT COUNT(*) FROM stg_customers` |
| DUP-03 | `SELECT COUNT(*) FROM stg_order_items` |
| DUP-04 | `SELECT COUNT(*) FROM stg_order_payments` |
| DUP-05 | `SELECT COUNT(*) FROM stg_reviews` |
| DUP-06 | `SELECT COUNT(*) FROM stg_products` |
| DUP-07 | `SELECT COUNT(*) FROM stg_sellers` |
| DUP-08 | `SELECT COUNT(*) FROM stg_geolocation` |
| REF-01 | `SELECT COUNT(*) FROM stg_order_items` |
| REF-02 | `SELECT COUNT(*) FROM stg_order_items` |
| REF-03 | `SELECT COUNT(*) FROM stg_order_items` |
| REF-04 | `SELECT COUNT(*) FROM stg_order_payments` |
| REF-05 | `SELECT COUNT(*) FROM stg_reviews` |
| REF-06 | `SELECT COUNT(*) FROM stg_orders` |
| REF-07 | `SELECT COUNT(*) FROM stg_orders` |
| REF-08 | `SELECT COUNT(*) FROM stg_orders` |
| REF-09 | `SELECT COUNT(*) FROM stg_customers` |
| REF-10 | `SELECT COUNT(*) FROM stg_sellers` |
| REF-11 | `SELECT COUNT(*) FROM stg_products` |
| NUL-01 | `SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered'` |
| NUL-02 | `SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered'` |
| NUL-03 | `SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) IN ('shipped','delivered')` |
| NUL-04 | `SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) <> 'delivered'` |
| NUL-05 | `SELECT COUNT(*) FROM stg_orders` |
| NUL-06 | `SELECT COUNT(*) FROM stg_orders` |
| NUL-07 | `SELECT COUNT(*) FROM stg_products` |
| TIM-01 | `SELECT COUNT(*) FROM stg_orders` |
| TIM-02 | `SELECT COUNT(*) FROM stg_orders` |
| TIM-03 | `SELECT COUNT(*) FROM stg_orders` |
| TIM-04 | `SELECT COUNT(*) FROM stg_orders` |
| TIM-05 | `SELECT COUNT(*) FROM stg_orders` |
| TIM-06 | `SELECT COUNT(*) FROM stg_orders` |
| TIM-07 | `SELECT COUNT(*) FROM stg_reviews` |
| TIM-08 | `SELECT COUNT(*) FROM stg_reviews` |
| DOM-01 | `SELECT COUNT(*) FROM stg_orders` |
| DOM-02 | `SELECT COUNT(*) FROM stg_order_payments` |
| DOM-03 | `SELECT COUNT(*) FROM stg_order_payments` |
| DOM-04 | `SELECT COUNT(*) FROM stg_order_payments` |
| DOM-05 | `SELECT COUNT(*) FROM stg_order_items` |
| DOM-06 | `SELECT COUNT(*) FROM stg_reviews` |
| DOM-07 | `SELECT COUNT(*) FROM stg_orders` |
| DOM-08 | `SELECT COUNT(*) FROM stg_products` |
| DOM-09 | `SELECT COUNT(*) FROM stg_customers` |
| CON-01 | `SELECT COUNT(*) FROM stg_orders o WHERE EXISTS (SELECT 1 FROM stg_order_items i WHERE i.order_id=o.order_id) AND EXISTS (SELECT 1 FROM stg_order_payments p WHERE p.order_id=o.order_id)` |
| CON-02 | `SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered'` |

规则 SQL 见 `SQL/governance/02_quality_checks.sql`。异常明细最多写入每规则1000条，完整数量写入 quality_check_summary；不得用样例数代替异常总数。

geo 同邮编多坐标与重复 customer_unique_id 不应被当作源数据垃圾：前者是源文件粒度与 A 主键不一致，后者是正常跨订单客户。review_id 冲突也需 A 复核模型；隔离后续行只是兼容现有主键的临时策略。

覆盖局限：暂存层原始键尚未统一 trim 后判重；子表序号格式、关键维表空键、坐标范围与评论敏感信息没有纳入45条SQL规则。隐私扫描另由 security_verify.py 执行。