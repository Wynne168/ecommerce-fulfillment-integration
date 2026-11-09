-- ============================================
-- 可观测性规则登记
-- 负责人：组员C（运行批次记录 processing_log 由组员B采集，本规则消费其 batch_id / status / 行数）
-- 说明：事件写入 observability_events，判定由 SRC/governance/governance_pipeline.py 的 evaluate_observability() 执行。
--       event_status: OK（正常，也记录，便于证明"检查过"）/ WARN（需关注）/ ALERT（需处理，批次状态置为 partial）
-- ============================================
REPLACE INTO observability_rules (obs_rule_id, category, rule_name, signal_source, condition_text, severity, response_action) VALUES
('OBS-RUN-01', '运行', '处理步骤失败', 'processing_log.status',
 '本批次任一步骤 status = ''failed''', 'critical', '批次置为 failed，停止发布到页面；保留上一成功批次'),
('OBS-RUN-02', '运行', '步骤长时间处于 running', 'processing_log.status, start_time',
 'status = ''running'' 且 start_time 早于当前时间 30 分钟（进程中断未回写）', 'warning', '人工确认进程状态，补写 end_time/status'),
('OBS-RUN-03', '运行', '源文件缺失或表头不符', 'batch_row_reconciliation.recon_status',
 'recon_status = ''MISSING''（文件不存在或表头与预期列不一致）', 'critical', '通知数据提供方/组员A核对源文件'),
('OBS-ROW-01', '行数', '源文件行数与暂存行数不一致', 'batch_row_reconciliation.source_rows/staged_rows',
 'staged_rows <> source_rows（存在格式错误行或载入中断）', 'critical', '检查 error_message 中的格式错误行'),
('OBS-ROW-02', '行数', '核心表行数不守恒', 'batch_row_reconciliation.core_rows/expected_core_rows',
 'core_rows <> staged_rows - quarantined_rows（地理表为去重后邮编数）', 'critical', '检查核心表写入步骤与约束冲突'),
('OBS-ROW-03', '行数', '行数相对基线漂移', 'batch_row_reconciliation.staged_rows vs 上一成功批次/基线',
 '|变化率| > 5% 为 WARN，> 20% 为 ALERT', 'warning', '确认源文件是否被截断、重复或换版'),
('OBS-QUA-01', '质量', '关键质量规则失败', 'quality_check_summary',
 'severity = ''critical'' 且 check_status = ''FAIL''', 'critical', '对应记录已隔离/标记；批次置为 partial，通知规则负责人'),
('OBS-QUA-02', '质量', '一般质量规则超阈值', 'quality_check_summary',
 'severity <> ''critical'' 且 check_status = ''FAIL''（异常率超过阈值）', 'warning', '复核阈值与异常样例'),
('OBS-QUA-03', '质量', '异常数量相对上一批突变', 'quality_check_summary.failed_rows',
 '|本批 - 上批| / 上批 > 50% 且绝对差 >= 10', 'warning', '排查上游变更'),
('OBS-QUA-04', '质量', '质量检查执行出错', 'quality_check_summary.check_status',
 'check_status = ''ERROR''（规则 SQL 执行失败）', 'critical', '修复规则 SQL，重新运行检查'),
('OBS-FRS-01', '时效', '处理时效（最近导入时间）', 'batch_data_time_profile.process_finished_at',
 '距最近一次成功处理超过 24 小时', 'warning', '检查调度；注意：只看处理时间，不看订单业务日期'),
('OBS-FRS-02', '时效', '业务时间回退', 'batch_data_time_profile.business_time_max',
 '本批最大下单时间早于上一成功批次（数据回退/换成旧版本）', 'warning', '核对源文件版本'),
('OBS-MET-01', '指标', '延迟订单数突变', 'v_delayed_orders_governed',
 '与上一成功批次相比变化 > 10%', 'warning', '结合质量规则与血缘排查口径或数据变化');

SELECT '可观测性规则登记完成' AS status;
