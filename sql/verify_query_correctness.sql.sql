-- ============================================
-- 查询验证脚本：核对查询正确性
-- 负责人：组员A
-- 说明：验证一单多商品、多条支付时，直接连接是否造成重复计数或金额放大
-- ============================================

-- ============================================
-- 验证1：一单多商品 - 直接JOIN vs 预聚合对比
-- ============================================

-- 选取有多条商品明细的订单进行验证
-- 步骤1：找出有多条商品明细的订单
SELECT order_id, COUNT(*) AS item_count
FROM order_items
GROUP BY order_id
HAVING COUNT(*) > 1
LIMIT 5;

-- 步骤2：用直接JOIN方式查询（会产生重复行）
-- 假设选取订单号 'order_id_example' 进行测试
SET @test_order_id = 'order_id_example';

-- 直接JOIN方式（有重复风险）
SELECT
    o.order_id,
    COUNT(oi.order_item_id) AS direct_item_count,
    SUM(oi.price) AS direct_total_price,
    SUM(oi.freight_value) AS direct_total_freight
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_id = @test_order_id;

-- 预聚合方式（正确）
SELECT
    o.order_id,
    COALESCE(item_agg.item_count, 0) AS aggregated_item_count,
    COALESCE(item_agg.total_price, 0) AS aggregated_total_price,
    COALESCE(item_agg.total_freight, 0) AS aggregated_total_freight
FROM orders o
LEFT JOIN (
    SELECT order_id,
           COUNT(order_item_id) AS item_count,
           SUM(price) AS total_price,
           SUM(freight_value) AS total_freight
    FROM order_items
    GROUP BY order_id
) item_agg ON o.order_id = item_agg.order_id
WHERE o.order_id = @test_order_id;

-- 步骤3：对比两种方式的差异（应完全一致）
-- 如果直接JOIN的SUM结果 != 预聚合的SUM结果，说明存在重复计数问题

-- ============================================
-- 验证2：一单多支付 - 直接JOIN vs 预聚合对比
-- ============================================

-- 步骤1：找出有多条支付记录的订单
SELECT order_id, COUNT(*) AS payment_count
FROM order_payments
GROUP BY order_id
HAVING COUNT(*) > 1
LIMIT 5;

-- 步骤2：直接JOIN方式（有金额放大风险）
SELECT
    o.order_id,
    COUNT(op.payment_sequential) AS direct_payment_count,
    SUM(op.payment_value) AS direct_total_payment
FROM orders o
JOIN order_payments op ON o.order_id = op.order_id
WHERE o.order_id = @test_order_id
GROUP BY o.order_id;

-- 步骤3：预聚合方式（正确）
SELECT
    o.order_id,
    COALESCE(payment_agg.payment_count, 0) AS aggregated_payment_count,
    COALESCE(payment_agg.total_payment, 0) AS aggregated_total_payment
FROM orders o
LEFT JOIN (
    SELECT order_id,
           COUNT(payment_sequential) AS payment_count,
           SUM(payment_value) AS total_payment
    FROM order_payments
    GROUP BY order_id
) payment_agg ON o.order_id = payment_agg.order_id
WHERE o.order_id = @test_order_id;

-- ============================================
-- 验证3：多表联合时的笛卡尔积问题
-- ============================================

-- 一单多商品(3个) + 多支付(2笔) = 直接JOIN产生 3x2=6行
-- 验证商品总金额是否被放大

-- 直接三表JOIN（有风险）
SELECT
    o.order_id,
    COUNT(DISTINCT oi.order_item_id) AS distinct_items,
    SUM(oi.price) AS sum_price_joined,
    COUNT(DISTINCT op.payment_sequential) AS distinct_payments,
    SUM(op.payment_value) AS sum_payment_joined
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN order_payments op ON o.order_id = op.order_id
WHERE o.order_id = @test_order_id
GROUP BY o.order_id;

-- 通过子查询预聚合（正确）
SELECT
    o.order_id,
    item_agg.item_count,
    item_agg.total_price,
    payment_agg.payment_count,
    payment_agg.total_payment
FROM orders o
JOIN (
    SELECT order_id,
           COUNT(order_item_id) AS item_count,
           SUM(price) AS total_price
    FROM order_items
    GROUP BY order_id
) item_agg ON o.order_id = item_agg.order_id
JOIN (
    SELECT order_id,
           COUNT(payment_sequential) AS payment_count,
           SUM(payment_value) AS total_payment
    FROM order_payments
    GROUP BY order_id
) payment_agg ON o.order_id = payment_agg.order_id
WHERE o.order_id = @test_order_id;

-- ============================================
-- 验证4：延迟订单查询正确性验证
-- ============================================

-- 步骤1：手动计算某个已送达订单的延迟天数
SET @verify_order_id = 'order_id_delivered_example';

SELECT
    order_id,
    order_estimated_delivery_date,
    order_delivered_customer_date,
    DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS calculated_delay_days,
    order_status
FROM orders
WHERE order_id = @verify_order_id;

-- 步骤2：用视图查询同一订单的延迟天数（应一致）
SELECT order_id, delay_days AS view_delay_days
FROM v_delayed_orders
WHERE order_id = @verify_order_id;

-- 步骤3：验证延迟订单总数
-- 方法A：直接统计
SELECT COUNT(*) AS manual_delayed_count
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL
  AND order_delivered_customer_date > order_estimated_delivery_date;

-- 方法B：用视图统计
SELECT COUNT(*) AS view_delayed_count
FROM v_delayed_orders;

-- 两种方法的结果应完全一致

-- ============================================
-- 验证5：数据完整性检查
-- ============================================

-- 检查订单明细中的order_id是否都存在于orders表
SELECT COUNT(*) AS orphan_items
FROM order_items oi
LEFT JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;

-- 检查支付记录中的order_id是否都存在于orders表
SELECT COUNT(*) AS orphan_payments
FROM order_payments op
LEFT JOIN orders o ON op.order_id = o.order_id
WHERE o.order_id IS NULL;

-- 检查金额一致性：订单明细总金额应接近支付总金额（允许小额差异）
SELECT
    o.order_id,
    COALESCE(item_total.total_price, 0) AS items_total,
    COALESCE(payment_total.total_payment, 0) AS payments_total,
    ABS(COALESCE(item_total.total_price, 0) - COALESCE(payment_total.total_payment, 0)) AS difference
FROM orders o
LEFT JOIN (
    SELECT order_id, SUM(price) AS total_price FROM order_items GROUP BY order_id
) item_total ON o.order_id = item_total.order_id
LEFT JOIN (
    SELECT order_id, SUM(payment_value) AS total_payment FROM order_payments GROUP BY order_id
) payment_total ON o.order_id = payment_total.order_id
WHERE ABS(COALESCE(item_total.total_price, 0) - COALESCE(payment_total.total_payment, 0)) > 0.02
LIMIT 20;

SELECT '查询验证脚本执行完成' AS status;
