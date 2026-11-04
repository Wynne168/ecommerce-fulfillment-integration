-- ============================================
-- 建表脚本：电商履约数据整合系统
-- 负责人：组员A
-- 说明：可重复执行（幂等），先删后建
-- ============================================

-- 注意：删除顺序与建表顺序相反，避免外键冲突
DROP TABLE IF EXISTS quality_check_results;
DROP TABLE IF EXISTS processing_log;
DROP TABLE IF EXISTS geolocation;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS orders;

-- ============================================
-- 1. 客户表
-- ============================================
CREATE TABLE customers (
    customer_id       VARCHAR(50)  NOT NULL,
    customer_unique_id VARCHAR(50) DEFAULT NULL,
    customer_zip_code_prefix VARCHAR(10) DEFAULT NULL,
    customer_city      VARCHAR(50)  DEFAULT NULL,
    customer_state     VARCHAR(10)  DEFAULT NULL,
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 2. 卖家表
-- ============================================
CREATE TABLE sellers (
    seller_id             VARCHAR(50) NOT NULL,
    seller_zip_code_prefix VARCHAR(10) DEFAULT NULL,
    seller_city            VARCHAR(50) DEFAULT NULL,
    seller_state           VARCHAR(10) DEFAULT NULL,
    PRIMARY KEY (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 3. 商品信息表
-- ============================================
CREATE TABLE products (
    product_id               VARCHAR(50) NOT NULL,
    product_category_name    VARCHAR(100) DEFAULT NULL,
    product_name_lenght      INT DEFAULT NULL,
    product_description_lenght INT DEFAULT NULL,
    product_photos_qty       INT DEFAULT NULL,
    product_weight_g         INT DEFAULT NULL,
    product_length_cm        INT DEFAULT NULL,
    product_height_cm        INT DEFAULT NULL,
    product_width_cm         INT DEFAULT NULL,
    PRIMARY KEY (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 4. 地理位置表
-- ============================================
CREATE TABLE geolocation (
    geolocation_zip_code_prefix VARCHAR(10) NOT NULL,
    geolocation_lat             DECIMAL(10,8) NOT NULL,
    geolocation_lng             DECIMAL(11,8) NOT NULL,
    geolocation_city            VARCHAR(50) DEFAULT NULL,
    geolocation_state           VARCHAR(10) DEFAULT NULL,
    PRIMARY KEY (geolocation_zip_code_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 5. 订单主表
-- ============================================
CREATE TABLE orders (
    order_id                    VARCHAR(50) NOT NULL,
    customer_id                 VARCHAR(50) NOT NULL,
    order_status                VARCHAR(20) DEFAULT NULL,
    order_purchase_timestamp    DATETIME DEFAULT NULL,
    order_approved_at           DATETIME DEFAULT NULL,
    order_delivered_carrier_date  DATETIME DEFAULT NULL,
    order_delivered_customer_date DATETIME DEFAULT NULL,
    order_estimated_delivery_date DATETIME DEFAULT NULL,
    PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 6. 订单明细表
-- ============================================
CREATE TABLE order_items (
    order_id             VARCHAR(50) NOT NULL,
    order_item_id        INT NOT NULL,
    product_id           VARCHAR(50) NOT NULL,
    seller_id            VARCHAR(50) NOT NULL,
    shipping_limit_date  DATETIME DEFAULT NULL,
    price                DECIMAL(10,2) NOT NULL,
    freight_value        DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_items_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_items_seller
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 7. 订单支付表
-- ============================================
CREATE TABLE order_payments (
    order_id            VARCHAR(50) NOT NULL,
    payment_sequential  INT NOT NULL,
    payment_type        VARCHAR(20) NOT NULL,
    payment_installments INT NOT NULL,
    payment_value       DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 8. 客户评价表
-- ============================================
CREATE TABLE reviews (
    review_id             VARCHAR(50) NOT NULL,
    order_id              VARCHAR(50) NOT NULL,
    review_score          INT DEFAULT NULL,
    review_comment_title  VARCHAR(200) DEFAULT NULL,
    review_comment_message TEXT DEFAULT NULL,
    review_creation_date  DATETIME DEFAULT NULL,
    review_answer_timestamp DATETIME DEFAULT NULL,
    PRIMARY KEY (review_id),
    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 9. 处理日志表（系统表）
-- ============================================
CREATE TABLE processing_log (
    log_id         INT AUTO_INCREMENT NOT NULL,
    batch_id       VARCHAR(50) NOT NULL,
    process_name   VARCHAR(50) NOT NULL,
    start_time     DATETIME NOT NULL,
    end_time       DATETIME DEFAULT NULL,
    input_rows     INT DEFAULT NULL,
    output_rows    INT DEFAULT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'running',
    error_message  TEXT DEFAULT NULL,
    PRIMARY KEY (log_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 10. 质量检查结果表（系统表）
-- ============================================
CREATE TABLE quality_check_results (
    check_id          INT AUTO_INCREMENT NOT NULL,
    batch_id          VARCHAR(50) NOT NULL,
    check_name        VARCHAR(50) NOT NULL,
    table_name        VARCHAR(50) NOT NULL,
    record_id         VARCHAR(50) DEFAULT NULL,
    issue_type        VARCHAR(50) NOT NULL,
    issue_description TEXT DEFAULT NULL,
    severity          VARCHAR(10) NOT NULL DEFAULT 'warning',
    checked_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (check_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 索引创建
-- ============================================
-- orders 表索引
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_orders_purchase_time ON orders(order_purchase_timestamp);
CREATE INDEX idx_orders_estimated_delivery ON orders(order_estimated_delivery_date);
CREATE INDEX idx_orders_delivered_customer ON orders(order_delivered_customer_date);

-- order_items 表索引
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_items_product ON order_items(product_id);
CREATE INDEX idx_items_seller ON order_items(seller_id);

-- order_payments 表索引
CREATE INDEX idx_payments_order ON order_payments(order_id);

-- reviews 表索引
CREATE INDEX idx_reviews_order ON reviews(order_id);

-- geolocation 表索引
CREATE INDEX idx_geo_zip ON geolocation(geolocation_zip_code_prefix);

-- ============================================
-- 视图创建
-- ============================================

-- 视图1：订单履约详情视图
CREATE OR REPLACE VIEW v_order_fulfillment AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    p.product_category_name,
    oi.price,
    oi.freight_value,
    op.payment_type,
    op.payment_sequential,
    op.payment_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN products p ON oi.product_id = p.product_id
LEFT JOIN order_payments op ON o.order_id = op.order_id;

-- 视图2：订单汇总视图（预聚合，避免重复计数）
CREATE OR REPLACE VIEW v_order_summary AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    COALESCE(item_agg.total_price, 0) AS total_price,
    COALESCE(item_agg.total_freight, 0) AS total_freight,
    COALESCE(item_agg.item_count, 0) AS item_count,
    COALESCE(payment_agg.total_payment, 0) AS total_payment,
    COALESCE(payment_agg.payment_count, 0) AS payment_count
FROM orders o
LEFT JOIN (
    SELECT order_id,
           SUM(price) AS total_price,
           SUM(freight_value) AS total_freight,
           COUNT(order_item_id) AS item_count
    FROM order_items
    GROUP BY order_id
) item_agg ON o.order_id = item_agg.order_id
LEFT JOIN (
    SELECT order_id,
           SUM(payment_value) AS total_payment,
           COUNT(payment_sequential) AS payment_count
    FROM order_payments
    GROUP BY order_id
) payment_agg ON o.order_id = payment_agg.order_id;

-- 视图3：延迟订单视图
CREATE OR REPLACE VIEW v_delayed_orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_estimated_delivery_date,
    order_delivered_customer_date,
    total_price,
    total_freight,
    item_count,
    total_payment,
    payment_count,
    DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS delay_days
FROM v_order_summary
WHERE order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL
  AND order_delivered_customer_date > order_estimated_delivery_date;

-- 视图4：延迟天数指标血缘追溯视图
CREATE OR REPLACE VIEW v_delay_metric_lineage AS
SELECT
    o.order_id,
    'order_estimated_delivery_date' AS metric_name,
    o.order_estimated_delivery_date AS source_value,
    'orders' AS source_table,
    'estimated - actual' AS calculation_rule
FROM orders o
WHERE o.order_estimated_delivery_date IS NOT NULL

UNION ALL

SELECT
    o.order_id,
    'order_delivered_customer_date' AS metric_name,
    o.order_delivered_customer_date AS source_value,
    'orders' AS source_table,
    'actual delivery' AS calculation_rule
FROM orders o
WHERE o.order_delivered_customer_date IS NOT NULL
  AND o.order_status = 'delivered';

SELECT '建表脚本执行完成' AS status;
