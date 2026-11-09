# 可观测性指标、异常判断与批次关联

C负责定义规则与判断条件；B负责采集运行记录、调度和页面接入。本次C为独立验证在processing_log中写入流水线记录，证明接口可运行，不宣称B的页面已集成。

## 1. 记录对象与阈值

每处理步骤记录batch_id、process_name、start_time、end_time、input_rows、output_rows、status、error_message。running表示开始，success/partial/failed表示终态；同一批次可有多个步骤，batch_id不是processing_log主键。质量汇总无异常也写PASS；只存异常明细会导致“未运行”和“零异常”无法区分。

| 规则 | 信号/判断条件 | 处理 |
|---|---|---|
| OBS-RUN-01 | 任一步骤failed | ALERT；失败批次禁止当作完整发布 |
| OBS-RUN-02 | running超过30分钟 | WARN；检查进程/补写终态 |
| OBS-RUN-03 | 源文件缺失或表头不符 | ALERT；A核对源文件 |
| OBS-ROW-01 | staged_rows≠source_rows | ALERT；定位跳过或格式错误记录 |
| OBS-ROW-02 | core_rows≠staged_rows−去重隔离行数；geo改用不同邮编数 | ALERT；核对转换/约束 |
| OBS-ROW-03 | 相对上一成功或partial批次行数变化绝对值>5%/20% | WARN/ALERT；首批使用A文档基线 |
| OBS-QUA-01 | critical规则FAIL | ALERT；按规则隔离/标记 |
| OBS-QUA-02 | 非critical规则超过异常率阈值 | WARN；A/C复核 |
| OBS-QUA-03 | 异常数变化>50%且绝对差≥10 | WARN；追查上游变更 |
| OBS-QUA-04 | 检查SQL执行ERROR | ALERT；区别“检查失败”与“未发现异常” |
| OBS-FRS-01 | 下次运行开始距上次完成>24小时 | WARN；当前仅运行时探测，无独立调度 |
| OBS-FRS-02 | 最大下单时间早于上一批 | WARN；可能使用旧文件，须A核验 |
| OBS-MET-01 | DATEDIFF≥1延迟订单数相对变化>10% | WARN；不直接认定业务恶化 |

这些阈值是课堂初始设置，不是经过长期统计验证的SLA。冻结历史数据应以相同源文件指纹做可比基线；新增订单流场景需要按每日/分区预期量，而不是用历史全量行数。

## 2. 时间语义

订单日期描述业务发生时间：本次下单时间实际范围2016-09-04 21:15:19至2018-10-17 17:30:18；最近导入时间是2026-11-09的process_started_at/process_finished_at，处理状态来自processing_log。

不能因最新订单停留在2018年而对这份历史教学快照发“数据八年没更新”的处理时效告警。业务时间回退与处理超时是两个独立问题，分别记录在batch_data_time_profile。

## 3. 与B批次关联示例

```sql
SET @batch_id = 'batch_20261109_223909';
SELECT process_name, start_time, end_time, input_rows, output_rows, status
FROM processing_log WHERE batch_id=@batch_id ORDER BY log_id;
SELECT rule_id, checked_rows, failed_rows, check_status
FROM quality_check_summary WHERE batch_id=@batch_id ORDER BY rule_id;
SELECT obs_rule_id, object_name, observed_value, expected_value, event_status
FROM observability_events WHERE batch_id=@batch_id ORDER BY event_id;
```

B建议把上述三份结果按batch_id分别读取或先聚合再连接。直接把某批次全部processing_log与全部质量明细连接，会产生步骤数×异常数的结果放大。不得使用表内最后一条记录猜测对应批次。

## 4. 实际验证

两个全量批次分别为batch_20261109_221808、batch_20261109_223909；45条规则异常数一致，源/暂存9表行数一致，核心8表均达到期望值，观测ALERT=0/WARN=0。质量本身23 PASS/22 WARN：质量WARN是已知异常，观测WARN是需要升级的运行信号，两者不能混同。

合成测试A触发sellers源3行、暂存2行的OBS-ROW-01 ALERT，并触发critical质量规则告警；B删除products文件后OBS-RUN-01/03均ALERT且批次failed；C截断orders使14→7，-50%触发OBS-ROW-03 ALERT。详见EVIDENCE/governance_test_evidence.md。

未验证的部分：30分钟running超时、24小时处理间隔、业务时间回退、规则SQL报错、核心表中途失败与全套质量漂移门限没有逐条故障注入。脚本只在运行时检查，尚无告警推送、仪表盘接入、定时探针、值班响应闭环和并发发布保护。分类为partial的批次仍可作为下次基线，生产应由B/组长定义哪些partial批次可比较。
