-- ============================================
-- 查询1：按订单号查询履约详情
-- 负责人：组员A
-- 说明：根据订单号查询完整的履约信息，包括订单基础信息、商品明细、支付信息
-- ============================================

-- 查询参数：将 'order_id_value' 替换为实际订单号
SET @target_order_id = '2e7a8482f6fb09756ca50c10d7bfc047';

-- 方式一：详细视图（含所有明细，一单多商品/多支付时会有重复行）
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
    p.product_category_name,
    oi.seller_id,
    oi.price AS item_price,
    oi.freight_value AS item_freight,
    op.payment_sequential,
    op.payment_type,
    op.payment_installments,
    op.payment_value AS payment_amount
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN products p ON oi.product_id = p.product_id
LEFT JOIN order_payments op ON o.order_id = op.order_id
WHERE o.order_id = @target_order_id
ORDER BY oi.order_item_id, op.payment_sequential;

-- 方式二：汇总视图（推荐用于展示，避免重复计数）
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
    COALESCE(item_agg.item_count, 0) AS total_items,
    COALESCE(item_agg.total_price, 0) AS total_product_price,
    COALESCE(item_agg.total_freight, 0) AS total_freight,
    COALESCE(item_agg.total_price, 0) + COALESCE(item_agg.total_freight, 0) AS order_total,
    COALESCE(payment_agg.payment_count, 0) AS total_payments,
    COALESCE(payment_agg.total_payment, 0) AS total_paid,
    CASE
        WHEN o.order_delivered_customer_date IS NOT NULL
             AND o.order_estimated_delivery_date IS NOT NULL
             AND o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)
        ELSE NULL
    END AS delay_days
FROM orders o
LEFT JOIN (
    SELECT order_id,
           COUNT(order_item_id) AS item_count,
           SUM(price) AS total_price,
           SUM(freight_value) AS total_freight
    FROM order_items
    GROUP BY order_id
) item_agg ON o.order_id = item_agg.order_id
LEFT JOIN (
    SELECT order_id,
           COUNT(payment_sequential) AS payment_count,
           SUM(payment_value) AS total_payment
    FROM order_payments
    GROUP BY order_id
) payment_agg ON o.order_id = payment_agg.order_id
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_id = @target_order_id;

-- 查询该订单的商品明细列表
SELECT
    oi.order_item_id,
    oi.product_id,
    p.product_category_name,
    oi.seller_id,
    oi.price,
    oi.freight_value
FROM order_items oi
LEFT JOIN products p ON oi.product_id = p.product_id
WHERE oi.order_id = @target_order_id;

-- 查询该订单的支付记录列表
SELECT
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
FROM order_payments
WHERE order_id = @target_order_id;
