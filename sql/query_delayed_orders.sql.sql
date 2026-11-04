-- ============================================
-- 查询2：按统一口径筛选延迟送达订单
-- 负责人：组员A
-- 说明：根据业务口径（实际送达日期 > 预计送达日期）筛选延迟订单
-- 统一口径定义：
--   - 仅统计 order_status = 'delivered' 的订单
--   - 实际送达日期和预计送达日期均不为空
--   - 延迟天数 = DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)
-- ============================================

-- 参数：可选的时间范围过滤
SET @start_date = '2016-09-01';
SET @end_date = '2018-09-01';

-- 查询1：延迟订单列表（使用预聚合视图，避免重复计数）
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_estimated_delivery_date,
    order_delivered_customer_date,
    delay_days,
    total_items,
    total_product_price,
    total_freight,
    total_payment,
    payment_count
FROM v_delayed_orders
WHERE order_purchase_timestamp >= @start_date
  AND order_purchase_timestamp < @end_date
ORDER BY delay_days DESC
LIMIT 100;

-- 查询2：延迟订单统计摘要
SELECT
    COUNT(*) AS total_delayed_orders,
    ROUND(AVG(delay_days), 2) AS avg_delay_days,
    MAX(delay_days) AS max_delay_days,
    MIN(delay_days) AS min_delay_days,
    ROUND(SUM(total_product_price), 2) AS total_delayed_value,
    ROUND(AVG(total_payment), 2) AS avg_delayed_payment
FROM v_delayed_orders
WHERE order_purchase_timestamp >= @start_date
  AND order_purchase_timestamp < @end_date;

-- 查询3：按月统计延迟订单数
SELECT
    DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS month,
    COUNT(*) AS delayed_count,
    ROUND(AVG(delay_days), 2) AS avg_delay,
    ROUND(SUM(total_product_price), 2) AS total_value
FROM v_delayed_orders
WHERE order_purchase_timestamp >= @start_date
  AND order_purchase_timestamp < @end_date
GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
ORDER BY month;

-- 查询4：按客户州统计延迟率
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT CASE WHEN d.order_id IS NOT NULL THEN o.order_id END) AS delayed_orders,
    ROUND(COUNT(DISTINCT CASE WHEN d.order_id IS NOT NULL THEN o.order_id END) /
          COUNT(DISTINCT o.order_id) * 100, 2) AS delay_rate_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN v_delayed_orders d ON o.order_id = d.order_id
WHERE o.order_purchase_timestamp >= @start_date
  AND o.order_purchase_timestamp < @end_date
GROUP BY c.customer_state
ORDER BY delay_rate_pct DESC;

-- 查询5：延迟订单的商品品类分布
SELECT
    p.product_category_name,
    COUNT(*) AS delayed_item_count,
    ROUND(SUM(oi.price), 2) AS total_price,
    ROUND(AVG(d.delay_days), 2) AS avg_delay_days
FROM v_delayed_orders d
JOIN order_items oi ON d.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE d.order_purchase_timestamp >= @start_date
  AND d.order_purchase_timestamp < @end_date
GROUP BY p.product_category_name
ORDER BY delayed_item_count DESC;

-- 查询6：延迟 vs 准时订单的物流时间对比
SELECT
    'delayed' AS category,
    COUNT(*) AS order_count,
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 2) AS avg_fulfillment_days,
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_approved_at)), 2) AS avg_seller_processing_days
FROM v_delayed_orders

UNION ALL

SELECT
    'on_time' AS category,
    COUNT(*) AS order_count,
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 2) AS avg_fulfillment_days,
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_approved_at)), 2) AS avg_seller_processing_days
FROM v_order_summary os
WHERE os.order_delivered_customer_date IS NOT NULL
  AND os.order_estimated_delivery_date IS NOT NULL
  AND os.order_delivered_customer_date <= os.order_estimated_delivery_date
  AND os.order_purchase_timestamp >= @start_date
  AND os.order_purchase_timestamp < @end_date;
