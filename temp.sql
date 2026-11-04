SET FOREIGN_KEY_CHECKS=0;  
-- ============================================
-- 数据导入脚本：电商履约数据整合系统
-- 负责人：组员A
-- 说明：使用 MySQL LOAD DATA INFILE 导入CSV数据
-- 注意：需根据实际情况修改文件路径
-- ============================================

-- 导入批次开始
INSERT INTO processing_log (batch_id, process_name, start_time, status)
VALUES (
    CONCAT('batch_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
    'import_all_data',
    NOW(),
    'running'
);

-- ============================================
-- 1. 导入客户表
-- ============================================
TRUNCATE TABLE customers;

LOAD DATA INFILE '/path/to/data/raw/olist_customers_dataset.csv'
INTO TABLE customers
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state);

-- ============================================
-- 2. 导入卖家表
-- ============================================
TRUNCATE TABLE sellers;

LOAD DATA INFILE '/path/to/data/raw/olist_sellers_dataset.csv'
INTO TABLE sellers
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(seller_id, seller_zip_code_prefix, seller_city, seller_state);

-- ============================================
-- 3. 导入商品信息表
-- ============================================
TRUNCATE TABLE products;

LOAD DATA INFILE 'F:/Assignment/data/raw/olist_orders_dataset.csv'
INTO TABLE products
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(product_id, product_category_name, product_name_lenght, product_description_lenght,
 product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm);

-- ============================================
-- 4. 导入地理位置表
-- ============================================
TRUNCATE TABLE geolocation;

LOAD DATA INFILE '/path/to/data/raw/olist_geolocation_dataset.csv'
INTO TABLE geolocation
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state);

-- ============================================
-- 5. 导入订单主表
-- ============================================
TRUNCATE TABLE orders;

LOAD DATA INFILE '/path/to/data/raw/olist_orders_dataset.csv'
INTO TABLE orders
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@order_id, @customer_id, @order_status, @order_purchase_timestamp,
 @order_approved_at, @order_delivered_carrier_date, @order_delivered_customer_date,
 @order_estimated_delivery_date)
SET
    order_id = TRIM(@order_id),
    customer_id = TRIM(@customer_id),
    order_status = TRIM(IFNULL(@order_status, '')),
    order_purchase_timestamp = STR_TO_DATE(TRIM(@order_purchase_timestamp), '%Y-%m-%d %H:%i:%s'),
    order_approved_at = STR_TO_DATE(TRIM(@order_approved_at), '%Y-%m-%d %H:%i:%s'),
    order_delivered_carrier_date = STR_TO_DATE(TRIM(@order_delivered_carrier_date), '%Y-%m-%d %H:%i:%s'),
    order_delivered_customer_date = STR_TO_DATE(TRIM(@order_delivered_customer_date), '%Y-%m-%d %H:%i:%s'),
    order_estimated_delivery_date = STR_TO_DATE(TRIM(@order_estimated_delivery_date), '%Y-%m-%d %H:%i:%s');

-- ============================================
-- 6. 导入订单明细表
-- ============================================
TRUNCATE TABLE order_items;

LOAD DATA INFILE '/path/to/data/raw/olist_order_items_dataset.csv'
INTO TABLE order_items
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@order_id, @order_item_id, @product_id, @seller_id, @shipping_limit_date, @price, @freight_value)
SET
    order_id = TRIM(@order_id),
    order_item_id = CAST(TRIM(@order_item_id) AS UNSIGNED),
    product_id = TRIM(@product_id),
    seller_id = TRIM(@seller_id),
    shipping_limit_date = STR_TO_DATE(TRIM(@shipping_limit_date), '%Y-%m-%d %H:%i:%s'),
    price = CAST(TRIM(@price) AS DECIMAL(10,2)),
    freight_value = CAST(TRIM(@freight_value) AS DECIMAL(10,2));

-- ============================================
-- 7. 导入订单支付表
-- ============================================
TRUNCATE TABLE order_payments;

LOAD DATA INFILE '/path/to/data/raw/olist_order_payments_dataset.csv'
INTO TABLE order_payments
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@order_id, @payment_sequential, @payment_type, @payment_installments, @payment_value)
SET
    order_id = TRIM(@order_id),
    payment_sequential = CAST(TRIM(@payment_sequential) AS UNSIGNED),
    payment_type = TRIM(@payment_type),
    payment_installments = CAST(TRIM(@payment_installments) AS UNSIGNED),
    payment_value = CAST(TRIM(@payment_value) AS DECIMAL(10,2));

-- ============================================
-- 8. 导入客户评价表
-- ============================================
TRUNCATE TABLE reviews;

LOAD DATA INFILE '/path/to/data/raw/olist_order_reviews_dataset.csv'
INTO TABLE reviews
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@review_id, @order_id, @review_score, @review_comment_title, @review_comment_message,
 @review_creation_date, @review_answer_timestamp)
SET
    review_id = TRIM(@review_id),
    order_id = TRIM(@order_id),
    review_score = CAST(TRIM(@review_score) AS UNSIGNED),
    review_comment_title = TRIM(IFNULL(@review_comment_title, '')),
    review_comment_message = TRIM(IFNULL(@review_comment_message, '')),
    review_creation_date = STR_TO_DATE(TRIM(@review_creation_date), '%Y-%m-%d %H:%i:%s'),
    review_answer_timestamp = STR_TO_DATE(TRIM(@review_answer_timestamp), '%Y-%m-%d %H:%i:%s');

-- ============================================
-- 导入完成，更新日志
-- ============================================
UPDATE processing_log
SET
    end_time = NOW(),
    input_rows = (
        SELECT SUM(cnt) FROM (
            SELECT COUNT(*) AS cnt FROM customers
            UNION ALL SELECT COUNT(*) FROM sellers
            UNION ALL SELECT COUNT(*) FROM products
            UNION ALL SELECT COUNT(*) FROM geolocation
            UNION ALL SELECT COUNT(*) FROM orders
            UNION ALL SELECT COUNT(*) FROM order_items
            UNION ALL SELECT COUNT(*) FROM order_payments
            UNION ALL SELECT COUNT(*) FROM reviews
        ) AS t
    ),
    output_rows = (
        SELECT SUM(cnt) FROM (
            SELECT COUNT(*) AS cnt FROM customers
            UNION ALL SELECT COUNT(*) FROM sellers
            UNION ALL SELECT COUNT(*) FROM products
            UNION ALL SELECT COUNT(*) FROM geolocation
            UNION ALL SELECT COUNT(*) FROM orders
            UNION ALL SELECT COUNT(*) FROM order_items
            UNION ALL SELECT COUNT(*) FROM order_payments
            UNION ALL SELECT COUNT(*) FROM reviews
        ) AS t
    ),
    status = 'success'
WHERE process_name = 'import_all_data' AND status = 'running'
ORDER BY log_id DESC LIMIT 1;

SELECT '数据导入脚本执行完成' AS status;
