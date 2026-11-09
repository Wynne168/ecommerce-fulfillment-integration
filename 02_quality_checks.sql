-- 质量检查脚本（只读，返回异常数量和样例；由 rules.py 自动导出）
-- 暂存层须已载入，结果写回由 governance_pipeline.py 执行。
-- 注意每条规则的分母不同，详见规则清单。

-- DUP-01 订单号重复: orders.order_id 为主键，同一 order_id 出现多行时，除首行外其余行判为重复。
SELECT 'DUP-01' rule_id, COUNT(*) failed_rows FROM (SELECT s.order_id AS record_key, s.src_row_num FROM stg_orders s JOIN (SELECT order_id, MIN(src_row_num) AS first_row FROM stg_orders GROUP BY order_id HAVING COUNT(*) > 1) d ON s.order_id = d.order_id AND s.src_row_num > d.first_row) hits;
SELECT s.order_id AS record_key, s.src_row_num FROM stg_orders s JOIN (SELECT order_id, MIN(src_row_num) AS first_row FROM stg_orders GROUP BY order_id HAVING COUNT(*) > 1) d ON s.order_id = d.order_id AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-02 客户ID重复: customers.customer_id 为主键，重复时除首行外隔离。
SELECT 'DUP-02' rule_id, COUNT(*) failed_rows FROM (SELECT s.customer_id AS record_key, s.src_row_num FROM stg_customers s JOIN (SELECT customer_id, MIN(src_row_num) AS first_row FROM stg_customers GROUP BY customer_id HAVING COUNT(*) > 1) d ON s.customer_id = d.customer_id AND s.src_row_num > d.first_row) hits;
SELECT s.customer_id AS record_key, s.src_row_num FROM stg_customers s JOIN (SELECT customer_id, MIN(src_row_num) AS first_row FROM stg_customers GROUP BY customer_id HAVING COUNT(*) > 1) d ON s.customer_id = d.customer_id AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-03 订单明细联合主键重复: (order_id, order_item_id) 为联合主键，重复时除首行外隔离。
SELECT 'DUP-03' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(s.order_id, '#', s.order_item_id) AS record_key, s.src_row_num FROM stg_order_items s JOIN (SELECT order_id, order_item_id, MIN(src_row_num) AS first_row FROM stg_order_items GROUP BY order_id, order_item_id HAVING COUNT(*) > 1) d ON s.order_id = d.order_id AND s.order_item_id = d.order_item_id AND s.src_row_num > d.first_row) hits;
SELECT CONCAT(s.order_id, '#', s.order_item_id) AS record_key, s.src_row_num FROM stg_order_items s JOIN (SELECT order_id, order_item_id, MIN(src_row_num) AS first_row FROM stg_order_items GROUP BY order_id, order_item_id HAVING COUNT(*) > 1) d ON s.order_id = d.order_id AND s.order_item_id = d.order_item_id AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-04 支付记录联合主键重复: (order_id, payment_sequential) 为联合主键，重复时除首行外隔离。
SELECT 'DUP-04' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(s.order_id, '#', s.payment_sequential) AS record_key, s.src_row_num FROM stg_order_payments s JOIN (SELECT order_id, payment_sequential, MIN(src_row_num) AS first_row FROM stg_order_payments GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1) d ON s.order_id = d.order_id AND s.payment_sequential = d.payment_sequential AND s.src_row_num > d.first_row) hits;
SELECT CONCAT(s.order_id, '#', s.payment_sequential) AS record_key, s.src_row_num FROM stg_order_payments s JOIN (SELECT order_id, payment_sequential, MIN(src_row_num) AS first_row FROM stg_order_payments GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1) d ON s.order_id = d.order_id AND s.payment_sequential = d.payment_sequential AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-05 评价ID对应多个订单: A 的模型以 review_id 为主键，但源数据中同一 review_id 关联多个 order_id。为满足主键约束，除首行外隔离并保留原始负载，建议 A 将主键改为 (review_id, order_id)。
SELECT 'DUP-05' rule_id, COUNT(*) failed_rows FROM (SELECT s.review_id AS record_key, s.src_row_num FROM stg_reviews s JOIN (SELECT review_id, MIN(src_row_num) AS first_row FROM stg_reviews GROUP BY review_id HAVING COUNT(*) > 1) d ON s.review_id = d.review_id AND s.src_row_num > d.first_row) hits;
SELECT s.review_id AS record_key, s.src_row_num FROM stg_reviews s JOIN (SELECT review_id, MIN(src_row_num) AS first_row FROM stg_reviews GROUP BY review_id HAVING COUNT(*) > 1) d ON s.review_id = d.review_id AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-06 商品ID重复: products.product_id 为主键，重复时除首行外隔离。
SELECT 'DUP-06' rule_id, COUNT(*) failed_rows FROM (SELECT s.product_id AS record_key, s.src_row_num FROM stg_products s JOIN (SELECT product_id, MIN(src_row_num) AS first_row FROM stg_products GROUP BY product_id HAVING COUNT(*) > 1) d ON s.product_id = d.product_id AND s.src_row_num > d.first_row) hits;
SELECT s.product_id AS record_key, s.src_row_num FROM stg_products s JOIN (SELECT product_id, MIN(src_row_num) AS first_row FROM stg_products GROUP BY product_id HAVING COUNT(*) > 1) d ON s.product_id = d.product_id AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-07 卖家ID重复: sellers.seller_id 为主键，重复时除首行外隔离。
SELECT 'DUP-07' rule_id, COUNT(*) failed_rows FROM (SELECT s.seller_id AS record_key, s.src_row_num FROM stg_sellers s JOIN (SELECT seller_id, MIN(src_row_num) AS first_row FROM stg_sellers GROUP BY seller_id HAVING COUNT(*) > 1) d ON s.seller_id = d.seller_id AND s.src_row_num > d.first_row) hits;
SELECT s.seller_id AS record_key, s.src_row_num FROM stg_sellers s JOIN (SELECT seller_id, MIN(src_row_num) AS first_row FROM stg_sellers GROUP BY seller_id HAVING COUNT(*) > 1) d ON s.seller_id = d.seller_id AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- DUP-08 邮编前缀多坐标: A 的模型以邮编前缀为主键，但源文件中一个前缀对应多行坐标。处置为修正：按前缀聚合，经纬度取平均值、城市/州取首行，而不是像原导入脚本那样静默保留首行。
SELECT 'DUP-08' rule_id, COUNT(*) failed_rows FROM (SELECT s.geolocation_zip_code_prefix AS record_key, s.src_row_num FROM stg_geolocation s JOIN (SELECT geolocation_zip_code_prefix, MIN(src_row_num) AS first_row FROM stg_geolocation GROUP BY geolocation_zip_code_prefix HAVING COUNT(*) > 1) d ON s.geolocation_zip_code_prefix = d.geolocation_zip_code_prefix AND s.src_row_num > d.first_row) hits;
SELECT s.geolocation_zip_code_prefix AS record_key, s.src_row_num FROM stg_geolocation s JOIN (SELECT geolocation_zip_code_prefix, MIN(src_row_num) AS first_row FROM stg_geolocation GROUP BY geolocation_zip_code_prefix HAVING COUNT(*) > 1) d ON s.geolocation_zip_code_prefix = d.geolocation_zip_code_prefix AND s.src_row_num > d.first_row ORDER BY src_row_num LIMIT 5;

-- REF-01 明细找不到订单: order_items.order_id 必须存在于 orders。
SELECT 'REF-01' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i LEFT JOIN stg_orders o ON o.order_id = i.order_id WHERE o.order_id IS NULL) hits;
SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i LEFT JOIN stg_orders o ON o.order_id = i.order_id WHERE o.order_id IS NULL ORDER BY src_row_num LIMIT 5;

-- REF-02 明细找不到商品: order_items.product_id 必须存在于 products。
SELECT 'REF-02' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i LEFT JOIN stg_products p ON p.product_id = i.product_id WHERE p.product_id IS NULL) hits;
SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i LEFT JOIN stg_products p ON p.product_id = i.product_id WHERE p.product_id IS NULL ORDER BY src_row_num LIMIT 5;

-- REF-03 明细找不到卖家: order_items.seller_id 必须存在于 sellers。
SELECT 'REF-03' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i LEFT JOIN stg_sellers s ON s.seller_id = i.seller_id WHERE s.seller_id IS NULL) hits;
SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i LEFT JOIN stg_sellers s ON s.seller_id = i.seller_id WHERE s.seller_id IS NULL ORDER BY src_row_num LIMIT 5;

-- REF-04 支付找不到订单: order_payments.order_id 必须存在于 orders。
SELECT 'REF-04' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p LEFT JOIN stg_orders o ON o.order_id = p.order_id WHERE o.order_id IS NULL) hits;
SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p LEFT JOIN stg_orders o ON o.order_id = p.order_id WHERE o.order_id IS NULL ORDER BY src_row_num LIMIT 5;

-- REF-05 评价找不到订单: reviews.order_id 必须存在于 orders。
SELECT 'REF-05' rule_id, COUNT(*) failed_rows FROM (SELECT r.review_id AS record_key, r.src_row_num FROM stg_reviews r LEFT JOIN stg_orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL) hits;
SELECT r.review_id AS record_key, r.src_row_num FROM stg_reviews r LEFT JOIN stg_orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL ORDER BY src_row_num LIMIT 5;

-- REF-06 订单找不到客户: orders.customer_id 必须存在于 customers。
SELECT 'REF-06' rule_id, COUNT(*) failed_rows FROM (SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o LEFT JOIN stg_customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL) hits;
SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o LEFT JOIN stg_customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL ORDER BY src_row_num LIMIT 5;

-- REF-07 订单没有任何明细: 反向关联：orders 中存在但 order_items 中没有明细的订单。
SELECT 'REF-07' rule_id, COUNT(*) failed_rows FROM (SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_order_items i WHERE i.order_id = o.order_id)) hits;
SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_order_items i WHERE i.order_id = o.order_id) ORDER BY src_row_num LIMIT 5;

-- REF-08 订单没有支付记录: 反向关联：orders 中存在但 order_payments 中没有记录的订单。
SELECT 'REF-08' rule_id, COUNT(*) failed_rows FROM (SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_order_payments p WHERE p.order_id = o.order_id)) hits;
SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_order_payments p WHERE p.order_id = o.order_id) ORDER BY src_row_num LIMIT 5;

-- REF-09 客户邮编无坐标: customers.customer_zip_code_prefix 在 geolocation 中找不到。
SELECT 'REF-09' rule_id, COUNT(*) failed_rows FROM (SELECT c.customer_id AS record_key, c.src_row_num FROM stg_customers c WHERE NOT EXISTS (SELECT 1 FROM stg_geolocation g WHERE g.geolocation_zip_code_prefix = c.customer_zip_code_prefix)) hits;
SELECT c.customer_id AS record_key, c.src_row_num FROM stg_customers c WHERE NOT EXISTS (SELECT 1 FROM stg_geolocation g WHERE g.geolocation_zip_code_prefix = c.customer_zip_code_prefix) ORDER BY src_row_num LIMIT 5;

-- REF-10 卖家邮编无坐标: sellers.seller_zip_code_prefix 在 geolocation 中找不到。
SELECT 'REF-10' rule_id, COUNT(*) failed_rows FROM (SELECT s.seller_id AS record_key, s.src_row_num FROM stg_sellers s WHERE NOT EXISTS (SELECT 1 FROM stg_geolocation g WHERE g.geolocation_zip_code_prefix = s.seller_zip_code_prefix)) hits;
SELECT s.seller_id AS record_key, s.src_row_num FROM stg_sellers s WHERE NOT EXISTS (SELECT 1 FROM stg_geolocation g WHERE g.geolocation_zip_code_prefix = s.seller_zip_code_prefix) ORDER BY src_row_num LIMIT 5;

-- REF-11 品类无英文翻译: 非空品类名在 product_category_name_translation 中找不到对应英文名。
SELECT 'REF-11' rule_id, COUNT(*) failed_rows FROM (SELECT p.product_id AS record_key, p.src_row_num FROM stg_products p WHERE NULLIF(TRIM(p.product_category_name), '') IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_category_translation t WHERE t.product_category_name = p.product_category_name)) hits;
SELECT p.product_id AS record_key, p.src_row_num FROM stg_products p WHERE NULLIF(TRIM(p.product_category_name), '') IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_category_translation t WHERE t.product_category_name = p.product_category_name) ORDER BY src_row_num LIMIT 5;

-- NUL-01 已送达但缺签收时间: order_status = 'delivered' 时 order_delivered_customer_date 不应为空。
SELECT 'NUL-01' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered' AND (NULLIF(TRIM(order_delivered_customer_date), '') IS NULL)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered' AND (NULLIF(TRIM(order_delivered_customer_date), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- NUL-02 已送达但缺支付批准时间: order_status = 'delivered' 时 order_approved_at 不应为空。
SELECT 'NUL-02' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered' AND (NULLIF(TRIM(order_approved_at), '') IS NULL)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered' AND (NULLIF(TRIM(order_approved_at), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- NUL-03 已发货/送达但缺承运时间: order_status IN ('shipped','delivered') 时 order_delivered_carrier_date 不应为空。
SELECT 'NUL-03' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) IN ('shipped','delivered') AND (NULLIF(TRIM(order_delivered_carrier_date), '') IS NULL)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) IN ('shipped','delivered') AND (NULLIF(TRIM(order_delivered_carrier_date), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- NUL-04 未送达状态却有签收时间: order_status <> 'delivered' 时出现 order_delivered_customer_date，状态与时间戳矛盾。
SELECT 'NUL-04' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) <> 'delivered' AND NOT (NULLIF(TRIM(order_delivered_customer_date), '') IS NULL)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) <> 'delivered' AND NOT (NULLIF(TRIM(order_delivered_customer_date), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- NUL-05 缺预计送达日期: order_estimated_delivery_date 为延迟天数的必需输入，不应为空。
SELECT 'NUL-05' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (NULLIF(TRIM(order_estimated_delivery_date), '') IS NULL)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (NULLIF(TRIM(order_estimated_delivery_date), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- NUL-06 订单关键字段为空: order_id、customer_id、order_purchase_timestamp 为 NOT NULL 关键字段。
SELECT 'NUL-06' rule_id, COUNT(*) failed_rows FROM (SELECT COALESCE(NULLIF(TRIM(order_id), ''), CONCAT('row#', src_row_num)) AS record_key, src_row_num FROM stg_orders WHERE (NULLIF(TRIM(order_id), '') IS NULL) OR (NULLIF(TRIM(customer_id), '') IS NULL) OR (NULLIF(TRIM(order_purchase_timestamp), '') IS NULL)) hits;
SELECT COALESCE(NULLIF(TRIM(order_id), ''), CONCAT('row#', src_row_num)) AS record_key, src_row_num FROM stg_orders WHERE (NULLIF(TRIM(order_id), '') IS NULL) OR (NULLIF(TRIM(customer_id), '') IS NULL) OR (NULLIF(TRIM(order_purchase_timestamp), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- NUL-07 商品品类为空: product_category_name 为空，品类分布中归入'未知'。
SELECT 'NUL-07' rule_id, COUNT(*) failed_rows FROM (SELECT product_id AS record_key, src_row_num FROM stg_products WHERE (NULLIF(TRIM(product_category_name), '') IS NULL)) hits;
SELECT product_id AS record_key, src_row_num FROM stg_products WHERE (NULLIF(TRIM(product_category_name), '') IS NULL) ORDER BY src_row_num LIMIT 5;

-- TIM-01 批准早于下单: order_approved_at >= order_purchase_timestamp（A 数据字典业务规则）。
SELECT 'TIM-01' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_approved_at) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_approved_at), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_approved_at) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_approved_at), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-02 交承运早于下单: order_delivered_carrier_date 不应早于 order_purchase_timestamp。
SELECT 'TIM-02' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-03 交承运早于支付批准: order_delivered_carrier_date >= order_approved_at（A 关系模式一般化约束）。
SELECT 'TIM-03' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_approved_at) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_approved_at), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_approved_at) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_approved_at), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-04 签收早于交承运: order_delivered_customer_date >= order_delivered_carrier_date（A 数据字典业务规则）。
SELECT 'TIM-04' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-05 签收早于下单: order_delivered_customer_date 不得早于 order_purchase_timestamp。
SELECT 'TIM-05' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-06 预计送达早于下单: order_estimated_delivery_date 不得早于 order_purchase_timestamp。
SELECT 'TIM-06' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-07 评价早于下单: review_creation_date 不应早于对应订单的下单时间。
SELECT 'TIM-07' rule_id, COUNT(*) failed_rows FROM (SELECT r.review_id AS record_key, r.src_row_num FROM stg_reviews r JOIN stg_orders o ON o.order_id = r.order_id WHERE (CASE WHEN TRIM(r.review_creation_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(r.review_creation_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(o.order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(o.order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT r.review_id AS record_key, r.src_row_num FROM stg_reviews r JOIN stg_orders o ON o.order_id = r.order_id WHERE (CASE WHEN TRIM(r.review_creation_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(r.review_creation_date), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(o.order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(o.order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- TIM-08 回复早于评价: review_answer_timestamp 不应早于 review_creation_date。
SELECT 'TIM-08' rule_id, COUNT(*) failed_rows FROM (SELECT review_id AS record_key, src_row_num FROM stg_reviews WHERE (CASE WHEN TRIM(review_answer_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(review_answer_timestamp), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(review_creation_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(review_creation_date), '%Y-%m-%d %H:%i:%s') END)) hits;
SELECT review_id AS record_key, src_row_num FROM stg_reviews WHERE (CASE WHEN TRIM(review_answer_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(review_answer_timestamp), '%Y-%m-%d %H:%i:%s') END) < (CASE WHEN TRIM(review_creation_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(review_creation_date), '%Y-%m-%d %H:%i:%s') END) ORDER BY src_row_num LIMIT 5;

-- DOM-01 订单状态不在域内: order_status 取值应属于实际业务域 ('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved')（已按源数据修订 A 的域约束）。
SELECT 'DOM-01' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(COALESCE(order_status, ''))) NOT IN ('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved')) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(COALESCE(order_status, ''))) NOT IN ('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved') ORDER BY src_row_num LIMIT 5;

-- DOM-02 支付方式不在域内: payment_type 应属于 ('credit_card','boleto','voucher','debit_card')。
SELECT 'DOM-02' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p WHERE LOWER(TRIM(COALESCE(p.payment_type, ''))) NOT IN ('credit_card','boleto','voucher','debit_card')) hits;
SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p WHERE LOWER(TRIM(COALESCE(p.payment_type, ''))) NOT IN ('credit_card','boleto','voucher','debit_card') ORDER BY src_row_num LIMIT 5;

-- DOM-03 支付金额非正: payment_value > 0（A 域约束）；无法解析为数字也视为异常。
SELECT 'DOM-03' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p WHERE (CASE WHEN TRIM(p.payment_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_value) AS DECIMAL(12,2)) END) IS NULL OR (CASE WHEN TRIM(p.payment_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_value) AS DECIMAL(12,2)) END) <= 0) hits;
SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p WHERE (CASE WHEN TRIM(p.payment_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_value) AS DECIMAL(12,2)) END) IS NULL OR (CASE WHEN TRIM(p.payment_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_value) AS DECIMAL(12,2)) END) <= 0 ORDER BY src_row_num LIMIT 5;

-- DOM-04 分期数小于1: payment_installments >= 1（A 域约束）。
SELECT 'DOM-04' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p WHERE (CASE WHEN TRIM(p.payment_installments) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_installments) AS SIGNED) END) IS NULL OR (CASE WHEN TRIM(p.payment_installments) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_installments) AS SIGNED) END) < 1) hits;
SELECT CONCAT(p.order_id, '#', p.payment_sequential) AS record_key, p.src_row_num FROM stg_order_payments p WHERE (CASE WHEN TRIM(p.payment_installments) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_installments) AS SIGNED) END) IS NULL OR (CASE WHEN TRIM(p.payment_installments) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(p.payment_installments) AS SIGNED) END) < 1 ORDER BY src_row_num LIMIT 5;

-- DOM-05 商品价格/运费非法: price > 0 且 freight_value >= 0，且均可解析为数字（核心表为 NOT NULL DECIMAL）。
SELECT 'DOM-05' rule_id, COUNT(*) failed_rows FROM (SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i WHERE (CASE WHEN TRIM(i.price) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.price) AS DECIMAL(12,2)) END) IS NULL OR (CASE WHEN TRIM(i.price) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.price) AS DECIMAL(12,2)) END) <= 0 OR (CASE WHEN TRIM(i.freight_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.freight_value) AS DECIMAL(12,2)) END) IS NULL OR (CASE WHEN TRIM(i.freight_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.freight_value) AS DECIMAL(12,2)) END) < 0) hits;
SELECT CONCAT(i.order_id, '#', i.order_item_id) AS record_key, i.src_row_num FROM stg_order_items i WHERE (CASE WHEN TRIM(i.price) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.price) AS DECIMAL(12,2)) END) IS NULL OR (CASE WHEN TRIM(i.price) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.price) AS DECIMAL(12,2)) END) <= 0 OR (CASE WHEN TRIM(i.freight_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.freight_value) AS DECIMAL(12,2)) END) IS NULL OR (CASE WHEN TRIM(i.freight_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(i.freight_value) AS DECIMAL(12,2)) END) < 0 ORDER BY src_row_num LIMIT 5;

-- DOM-06 评分不在1-5: review_score ∈ {1,2,3,4,5}。
SELECT 'DOM-06' rule_id, COUNT(*) failed_rows FROM (SELECT review_id AS record_key, src_row_num FROM stg_reviews WHERE TRIM(COALESCE(review_score, '')) NOT IN ('1','2','3','4','5')) hits;
SELECT review_id AS record_key, src_row_num FROM stg_reviews WHERE TRIM(COALESCE(review_score, '')) NOT IN ('1','2','3','4','5') ORDER BY src_row_num LIMIT 5;

-- DOM-07 订单时间戳无法解析: 非空时间戳必须符合 'YYYY-MM-DD HH:MM:SS' 且为合法日期；否则修正为 NULL 并标记，避免像 pandas errors='coerce' 那样静默变成空值。
SELECT 'DOM-07' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (NOT (NULLIF(TRIM(order_purchase_timestamp), '') IS NULL) AND (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_approved_at), '') IS NULL) AND (CASE WHEN TRIM(order_approved_at) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_approved_at), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_delivered_carrier_date), '') IS NULL) AND (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_delivered_customer_date), '') IS NULL) AND (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_estimated_delivery_date), '') IS NULL) AND (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END) IS NULL)) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE (NOT (NULLIF(TRIM(order_purchase_timestamp), '') IS NULL) AND (CASE WHEN TRIM(order_purchase_timestamp) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_purchase_timestamp), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_approved_at), '') IS NULL) AND (CASE WHEN TRIM(order_approved_at) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_approved_at), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_delivered_carrier_date), '') IS NULL) AND (CASE WHEN TRIM(order_delivered_carrier_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_delivered_customer_date), '') IS NULL) AND (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) IS NULL) OR (NOT (NULLIF(TRIM(order_estimated_delivery_date), '') IS NULL) AND (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END) IS NULL) ORDER BY src_row_num LIMIT 5;

-- DOM-08 商品重量/尺寸非正: 非空的重量与尺寸应 > 0。
SELECT 'DOM-08' rule_id, COUNT(*) failed_rows FROM (SELECT product_id AS record_key, src_row_num FROM stg_products WHERE (CASE WHEN TRIM(product_weight_g) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_weight_g) AS SIGNED) END) <= 0 OR (CASE WHEN TRIM(product_length_cm) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_length_cm) AS SIGNED) END) <= 0 OR (CASE WHEN TRIM(product_height_cm) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_height_cm) AS SIGNED) END) <= 0 OR (CASE WHEN TRIM(product_width_cm) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_width_cm) AS SIGNED) END) <= 0) hits;
SELECT product_id AS record_key, src_row_num FROM stg_products WHERE (CASE WHEN TRIM(product_weight_g) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_weight_g) AS SIGNED) END) <= 0 OR (CASE WHEN TRIM(product_length_cm) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_length_cm) AS SIGNED) END) <= 0 OR (CASE WHEN TRIM(product_height_cm) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_height_cm) AS SIGNED) END) <= 0 OR (CASE WHEN TRIM(product_width_cm) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(product_width_cm) AS SIGNED) END) <= 0 ORDER BY src_row_num LIMIT 5;

-- DOM-09 州代码格式错误: customer_state 应为两位大写字母（如 SP、RJ）。
SELECT 'DOM-09' rule_id, COUNT(*) failed_rows FROM (SELECT customer_id AS record_key, src_row_num FROM stg_customers WHERE NOT REGEXP_LIKE(TRIM(COALESCE(customer_state, '')), '^[A-Z]{2}$', 'c')) hits;
SELECT customer_id AS record_key, src_row_num FROM stg_customers WHERE NOT REGEXP_LIKE(TRIM(COALESCE(customer_state, '')), '^[A-Z]{2}$', 'c') ORDER BY src_row_num LIMIT 5;

-- CON-01 支付总额与商品+运费不符: 同一订单 |SUM(payment_value) - SUM(price + freight_value)| > 1.00 视为金额不一致（分期利息、优惠券可造成小额差异，故容差取 1.00）。
SELECT 'CON-01' rule_id, COUNT(*) failed_rows FROM (SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o JOIN (SELECT order_id, SUM((CASE WHEN TRIM(price) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(price) AS DECIMAL(12,2)) END) + (CASE WHEN TRIM(freight_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(freight_value) AS DECIMAL(12,2)) END)) AS amt FROM stg_order_items GROUP BY order_id) i ON i.order_id = o.order_id JOIN (SELECT order_id, SUM((CASE WHEN TRIM(payment_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(payment_value) AS DECIMAL(12,2)) END)) AS paid FROM stg_order_payments GROUP BY order_id) p ON p.order_id = o.order_id WHERE ABS(p.paid - i.amt) > 1.00) hits;
SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o JOIN (SELECT order_id, SUM((CASE WHEN TRIM(price) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(price) AS DECIMAL(12,2)) END) + (CASE WHEN TRIM(freight_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(freight_value) AS DECIMAL(12,2)) END)) AS amt FROM stg_order_items GROUP BY order_id) i ON i.order_id = o.order_id JOIN (SELECT order_id, SUM((CASE WHEN TRIM(payment_value) REGEXP '^-?[0-9]+([.][0-9]+)?$' THEN CAST(TRIM(payment_value) AS DECIMAL(12,2)) END)) AS paid FROM stg_order_payments GROUP BY order_id) p ON p.order_id = o.order_id WHERE ABS(p.paid - i.amt) > 1.00 ORDER BY src_row_num LIMIT 5;

-- CON-02 晚于预计时刻但延迟天数为0: 已送达订单签收时间 > 预计送达时间（预计时间均为 00:00:00），但 DATEDIFF = 0（当天签收）。'实际 > 预计' 与 '延迟天数 > 0' 两种口径对这些订单结论相反，需组长确认统一口径。
SELECT 'CON-02' rule_id, COUNT(*) failed_rows FROM (SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered' AND (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) > (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END) AND DATEDIFF((CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END), (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END)) = 0) hits;
SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered' AND (CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END) > (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END) AND DATEDIFF((CASE WHEN TRIM(order_delivered_customer_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_delivered_customer_date), '%Y-%m-%d %H:%i:%s') END), (CASE WHEN TRIM(order_estimated_delivery_date) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN STR_TO_DATE(TRIM(order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s') END)) = 0 ORDER BY src_row_num LIMIT 5;
