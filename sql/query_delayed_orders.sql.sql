-- 设置查询的时间段参数
SET @start_date = '2016-09-01';
SET @end_date = '2018-09-01';

-- 查询延迟订单及详细信息
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_estimated_delivery_date,
    o.order_delivered_customer_date,
    CASE
        WHEN o.order_delivered_customer_date IS NOT NULL
             AND o.order_estimated_delivery_date IS NOT NULL
             AND o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)
        ELSE 0
    END AS delay_days,
    COALESCE(item_agg.total_items, 0) AS total_items,
    COALESCE(item_agg.total_product_price, 0) AS total_product_price,
    COALESCE(item_agg.total_freight, 0) AS total_freight,
    COALESCE(pay_agg.total_payment, 0) AS total_payment,
    COALESCE(pay_agg.payment_count, 0) AS payment_count
FROM orders o
LEFT JOIN (
    SELECT order_id, 
           COUNT(*) AS total_items, 
           SUM(price) AS total_product_price, 
           SUM(freight_value) AS total_freight
    FROM order_items
    GROUP BY order_id
) item_agg ON o.order_id = item_agg.order_id
LEFT JOIN (
    SELECT order_id, 
           COUNT(*) AS payment_count, 
           SUM(payment_value) AS total_payment
    FROM order_payments
    GROUP BY order_id
) pay_agg ON o.order_id = pay_agg.order_id
WHERE o.order_purchase_timestamp >= @start_date
  AND o.order_purchase_timestamp < @end_date
  AND o.order_delivered_customer_date > o.order_estimated_delivery_date
ORDER BY delay_days DESC
LIMIT 100;