-- 组员C只读演示与B接入查询。不得用root凭据投屏；不修改业务数据。
USE ecommerce_fulfillment;
SET @batch_id = 'batch_20261109_223909';
-- B: 步骤、质量、观测分别读取，避免不同粒度直接JOIN放大。
SELECT batch_id,process_name,start_time,end_time,input_rows,output_rows,status
FROM processing_log WHERE batch_id=@batch_id ORDER BY log_id;
SELECT rule_id,table_name,checked_rows,failed_rows,fail_rate,check_status
FROM quality_check_summary WHERE batch_id=@batch_id ORDER BY rule_id;
SELECT obs_rule_id,object_name,metric_name,observed_value,expected_value,event_status
FROM observability_events WHERE batch_id=@batch_id ORDER BY event_id;
-- 真实异常：canceled却有签收；造成A视图多计一笔。
SET @anomaly='1950d777989f6a877539f53795b4c3c3';
SELECT * FROM v_delay_days_trace WHERE order_id=@anomaly;
SELECT * FROM quality_check_results WHERE batch_id=@batch_id AND check_name='NUL-04' AND record_id=@anomaly;
SELECT order_id,order_status,delay_days FROM v_delayed_orders WHERE order_id=@anomaly;
SELECT order_id,delay_days FROM v_delayed_orders_governed WHERE order_id=@anomaly;
-- 15天真实指标，逐单血缘到原文件第9914条记录。
SET @metric_order='01cbdb2a8c075eaf248af643b3389f73';
SELECT order_id,delay_days,quality_status,flag_rules FROM v_delayed_orders_governed WHERE order_id=@metric_order;
SELECT * FROM v_delay_days_trace WHERE order_id=@metric_order;
SELECT * FROM metric_lineage WHERE metric_id='delay_days' ORDER BY step_no;
-- 三种口径比较，不擅自替组长确认最终口径。
SELECT (SELECT COUNT(*) FROM v_delayed_orders) a_view_count,
       (SELECT COUNT(*) FROM orders WHERE order_status='delivered'
          AND order_delivered_customer_date>order_estimated_delivery_date) delivered_timestamp_count,
       (SELECT COUNT(*) FROM v_delayed_orders_governed) delivered_day_count;
