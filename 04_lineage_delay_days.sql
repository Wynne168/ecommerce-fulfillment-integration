-- ============================================
-- 指标血缘：延迟天数（delay_days）治理视图与血缘登记
-- 负责人：组员C（指标定义来自组员A《来源字段及转换说明》，页面接入由组员B负责）
-- 说明：
--   1. 不修改 A 的 v_delayed_orders，新增 v_delayed_orders_governed 作为"治理口径"视图，差异：
--      (a) 限定 order_status = 'delivered'（A 的视图未限定，导致计入 1 笔 canceled 订单，7827 vs 7826）；
--      (b) 以 delay_days >= 1 判定延迟，与"延迟天数 > 0 表示延迟"一致（预计送达时间均为 00:00:00，
--          当天签收按准时处理）；同时保留 late_by_timestamp 供组长确认口径时对照；
--      (c) 附带当前批次的质量标记 flag_rules，页面可提示"该订单存在数据质量问题"。
--   2. v_delay_days_trace 将页面上的每个 delay_days 追溯到暂存层原始字符串与 CSV 行号。
--   3. 可重复执行。
-- ============================================

-- 当前批次：按 processing_log.log_id 选择最新已有质量汇总的运行/成功/部分成功批次。
-- 不用字符串 MAX(batch_id)，避免不同批次前缀或并发时错选。尚不支持并发发布。
CREATE OR REPLACE VIEW v_governance_current_batch AS
SELECT p.batch_id FROM processing_log p
WHERE p.process_name = 'pipeline' AND p.status IN ('running','success','partial')
  AND EXISTS (SELECT 1 FROM quality_check_summary s WHERE s.batch_id = p.batch_id)
ORDER BY p.log_id DESC LIMIT 1;

-- 当前批次的订单级质量标记（一个订单一行）
CREATE OR REPLACE VIEW v_order_quality_flags AS
SELECT f.record_key AS order_id,
       f.batch_id,
       GROUP_CONCAT(DISTINCT f.rule_id ORDER BY f.rule_id SEPARATOR ',') AS flag_rules,
       COUNT(DISTINCT f.rule_id) AS flag_count
FROM data_quality_flags f
JOIN v_governance_current_batch b ON f.batch_id = b.batch_id
WHERE f.table_name = 'orders'
GROUP BY f.record_key, f.batch_id;

-- 治理口径的延迟订单视图（页面"延迟订单查询"建议使用）
CREATE OR REPLACE VIEW v_delayed_orders_governed AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_estimated_delivery_date,
    o.order_delivered_customer_date,
    DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) AS delay_days,
    (o.order_delivered_customer_date > o.order_estimated_delivery_date)        AS late_by_timestamp,
    COALESCE(q.flag_rules, '')                                                 AS flag_rules,
    CASE WHEN q.flag_count > 0 THEN 'FLAGGED' ELSE 'OK' END                    AS quality_status
FROM orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN v_order_quality_flags q ON q.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
  AND DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) >= 1;

-- 逐单血缘追溯：页面值 -> 核心表值 -> 暂存层原始字符串 -> 源文件与行号 -> 批次
CREATE OR REPLACE VIEW v_delay_days_trace AS
SELECT
    o.order_id,
    DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) AS delay_days,
    o.order_status,
    o.order_delivered_customer_date        AS core_delivered_customer_date,
    o.order_estimated_delivery_date        AS core_estimated_delivery_date,
    s.order_delivered_customer_date        AS raw_delivered_customer_date,
    s.order_estimated_delivery_date        AS raw_estimated_delivery_date,
    s.order_status                         AS raw_order_status,
    s.src_file,
    s.src_row_num,
    s.src_row_num + 1                      AS csv_line_no,
    s.batch_id,
    COALESCE(q.flag_rules, '')             AS flag_rules,
    CASE WHEN g.order_id IS NOT NULL THEN 'Y' ELSE 'N' END AS in_governed_delay_view
FROM orders o
JOIN v_governance_current_batch b ON 1=1
JOIN stg_orders s
  ON s.order_id = o.order_id
 AND s.batch_id = b.batch_id
 AND NOT EXISTS (SELECT 1 FROM data_quarantine dq
                 WHERE dq.batch_id = s.batch_id AND dq.table_name = 'orders' AND dq.src_row_num = s.src_row_num)
LEFT JOIN v_order_quality_flags q ON q.order_id = o.order_id
LEFT JOIN v_delayed_orders_governed g ON g.order_id = o.order_id;

-- 血缘登记（结构化，可在页面或报告中直接查询）
DELETE FROM metric_lineage WHERE metric_id = 'delay_days';
INSERT INTO metric_lineage (metric_id, step_no, layer_name, object_name, field_names, rule_text, condition_text, owner) VALUES
('delay_days', 1, '源文件', 'archive/olist_orders_dataset.csv',
 'order_status, order_delivered_customer_date, order_estimated_delivery_date',
 'Olist 原始 CSV，时间为 YYYY-MM-DD HH:MM:SS 字符串；预计送达时间均为 00:00:00', '文件存在且表头 8 列一致', '组员A'),
('delay_days', 2, '暂存层', 'stg_orders',
 'order_status, order_delivered_customer_date, order_estimated_delivery_date, src_row_num, batch_id',
 '按原样载入字符串，记录 batch_id、src_file、src_row_num（CSV 第 N 条记录 = 第 N+1 行）', '源行数 = 暂存行数（OBS-ROW-01）', '组员C'),
('delay_days', 3, '质量检查', 'quality_check_summary / data_quality_flags',
 'NUL-01, NUL-04, NUL-05, DOM-07, TIM-04, TIM-05, TIM-06, CON-02',
 '缺签收时间、非送达却有签收、缺预计日期、时间戳无法解析、时间顺序矛盾、口径冲突', '结果按 batch_id 记录', '组员C'),
('delay_days', 4, '核心表', 'orders',
 'order_status, order_delivered_customer_date, order_estimated_delivery_date',
 'TRIM + LOWER(status)；STR_TO_DATE(''%Y-%m-%d %H:%i:%s'')，非法值修正为 NULL 并标记（DOM-07）', '排除隔离区记录', '组员A/组员C'),
('delay_days', 5, '指标视图', 'v_delayed_orders_governed',
 'delay_days',
 'delay_days = DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)',
 'order_status = ''delivered'' AND 两个日期非空 AND delay_days >= 1', '组员C（口径待组长确认）'),
('delay_days', 6, '页面', '原型：延迟订单查询页 / 报告延迟统计图',
 'order_id, delay_days, quality_status, flag_rules',
 '按 delay_days 降序展示；FLAGGED 订单显示质量提示', '按下单时间范围筛选', '组员B'),
('delay_days', 7, '可观测性', 'observability_events',
 'OBS-MET-01 delayed_order_count',
 '每批记录延迟订单数，与上一批相比变化 > 10% 告警', '与 processing_log.batch_id 关联', '组员C');

SELECT '血缘视图与登记完成' AS status;
