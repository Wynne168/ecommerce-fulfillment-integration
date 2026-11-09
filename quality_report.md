# 数据质量检查报告

负责人：组员C。执行环境：MySQL 8.0.46、Python 3.15.0rc1；报告批次 `batch_20261109_223909`。

本报告是 archive 全量 CSV 的实际检查结果，不是示例结果。两个全量批次的45条异常数量一致；主报告采用第二批次快照。源文件未改写，未修改 MYSQL 中 A/B 的既有文件。

9个源文件合计 1,550,922 条数据记录（不含表头）。共45条质量规则：PASS=23、WARN=22。批次 status=success 意味着运行完成且未触发观测升级，不意味着数据完全无异常。

## 1. 输入、隔离与输出行数

| 表 | CSV行数 | 暂存行数 | 隔离行数（去重计） | 核心行数 | 期望核心行数 | 核对 |
|---|---:|---:|---:|---:|---:|---|
| category_translation | 71 | 71 | 0 | - | - | OK |
| customers | 99441 | 99441 | 0 | 99441 | 99441 | OK |
| geolocation | 1000163 | 1000163 | 0 | 19015 | 19015 | OK |
| order_items | 112650 | 112650 | 0 | 112650 | 112650 | OK |
| order_payments | 103886 | 103886 | 0 | 103886 | 103886 | OK |
| orders | 99441 | 99441 | 0 | 99441 | 99441 | OK |
| products | 32951 | 32951 | 0 | 32951 | 32951 | OK |
| reviews | 99224 | 99224 | 814 | 98410 | 98410 | OK |
| sellers | 3095 | 3095 | 0 | 3095 | 3095 | OK |

geo 1000163→19015 是按邮编前缀聚合，不是98%数据损坏；评价99224−814=98410，是为兼容A的 review_id 主键隔离了后续记录。分类翻译表71行仅留在暂存层参与关联检查，A未建其核心表。

## 2. 45条规则实测

| 规则 | 表 | 检查行数（分母） | 异常数 | 异常率 | 阈值 | 状态 | 处置 | 样例键（最多5条） |
|---|---|---:|---:|---:|---:|---|---|---|
| DUP-01 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DUP-02 | customers | 99441 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DUP-03 | order_items | 112650 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DUP-04 | order_payments | 103886 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DUP-05 | reviews | 99224 | 814 | 0.8204% | 1.5000% | WARN | quarantine | 3242cc306a9218d0377831e175d62fbf, 308316408775d1600dad81bd3184556d, 8ee90ac383cf825bb7f4756130d4e74a, d433c252647c51309432ca0b763f969b, 03a6a25db577d0689440933055111897 |
| DUP-06 | products | 32951 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DUP-07 | sellers | 3095 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DUP-08 | geolocation | 1000163 | 981148 | 98.0988% | 100.0000% | WARN | fix | 01046, 01013, 01012, 01037, 01046 |
| REF-01 | order_items | 112650 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| REF-02 | order_items | 112650 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| REF-03 | order_items | 112650 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| REF-04 | order_payments | 103886 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| REF-05 | reviews | 99224 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| REF-06 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| REF-07 | orders | 99441 | 775 | 0.7794% | 1.2000% | WARN | flag | 8e24261a7e58791d10cb1bf9da94df5c, c272bcd21c287498b4883c7512019702, 37553832a3a89c9b2db59701c357ca67, d57e15fb07fd180f06ab3926b39edcd2, 00b1cb0320190ca0daa2c88b35206009 |
| REF-08 | orders | 99441 | 1 | 0.0010% | 0.0500% | WARN | flag | bfbd0f9bdef84302105ad712db648a6c |
| REF-09 | customers | 99441 | 278 | 0.2796% | 0.5000% | WARN | flag | ecb1725b26e8b8c458181455dfa434ea, bcf86029aeed4ed8bac0e16eb14c22f5, f4302056f0c58570522590f8181de2c7, 03bbe0ce5c28e05f22917607db798818, ad4950aded55c2ea376be59506456d68 |
| REF-10 | sellers | 3095 | 7 | 0.2262% | 0.5000% | WARN | flag | 5962468f885ea01a1b6a97a218797b0a, 2aafae69bf4c41fbd94053d9413e87ee, 2a50b7ee5aebecc6fd0ff9784a4747d6, 2e90cb1677d35cfe24eef47d441b7c87, 0b3f27369a4d8df98f7eb91077e438ac |
| REF-11 | products | 32951 | 13 | 0.0395% | 0.5000% | WARN | flag | 0105b5323d24fc655f73052694dbbb3a, 6fd83eb3e0799b775e4f946bd66657c0, 5d923ead886c44b86845f69e50520c3e, 6727051471a0fc4a0e7737b57bff2549, bed164d9d628cf0593003389c535c6e0 |
| NUL-01 | orders | 96478 | 8 | 0.0083% | 0.0150% | WARN | flag | 2d1e2d5bf4dc7227b3bfebb81328c15f, f5dd62b788049ad9fc0526e3ad11a097, 2ebdfc4f15f23b91474edf87475f108e, e69f75a717d64fc5ecdfae42b2e8e086, 0d3268bad9b086af767785e3f0fc0133 |
| NUL-02 | orders | 96478 | 14 | 0.0145% | 0.0300% | WARN | flag | e04abd8149ef81b95221e88f6ed9ab6a, 8a9adc69528e1001fc68dd0aaebbb54a, 7013bcfc1c97fe719a7b5e05e61c12db, 5cf925b116421afa85ee25e99b4c34fb, 12a95a3c06dbaec84bcfb0e2da5d228a |
| NUL-03 | orders | 97585 | 2 | 0.0020% | 0.0100% | WARN | flag | 2aa91108853cecb43c84a5dc5b277475, 2d858f451373b04fb5c984a1cc2defaf |
| NUL-04 | orders | 2963 | 6 | 0.2025% | 0.4000% | WARN | flag | 1950d777989f6a877539f53795b4c3c3, dabf2b0e35b423f94618bf965fcb7514, 770d331c84e5b214bd9dc70a10b829d0, 8beb59392e21af5eb9547ae1a9938d06, 65d1e226dfaeb8cdc42f665422522d14 |
| NUL-05 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | flag | - |
| NUL-06 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| NUL-07 | products | 32951 | 610 | 1.8512% | 3.0000% | WARN | flag | a41e356c76fab66334f36de622ecbd3a, d8dee61c2034d6d075997acef1870e9b, 56139431d72cd51f19eb9f7dae4d1617, 46b48281eb6d663ced748f324108c733, 5fb61f482620cb672f5e586bb132eae9 |
| TIM-01 | orders | 99441 | 0 | 0.0000% | 0.1000% | PASS | flag | - |
| TIM-02 | orders | 99441 | 166 | 0.1669% | 0.2500% | WARN | flag | b9afddbdcfadc9a87b41a83271c3e888, ad133696906f6a78826daa0911b7daec, 74e033208dc13a7b8127eb8e73d09b76, a6b58794fd2ba533359a76c08df576e3, 5792e0b1c8c8a2bf53af468c9a422c88 |
| TIM-03 | orders | 99441 | 1359 | 1.3666% | 2.0000% | WARN | flag | dcb36b511fcac050b97cd5c05de84dc3, 688052146432ef8253587b930b01a06d, 58d4c4747ee059eeeb865b349b41f53a, 412fccb2b44a99b36714bca3fef8ad7b, 56a4ac10a4a8f2ba7693523bb439eede |
| TIM-04 | orders | 99441 | 23 | 0.0231% | 0.0400% | WARN | flag | a1abeb653a4d4cd1e142ccb8c82cd069, 383aa8b2724fe452d9ccd9934a8c628b, cb1134f9010d242e9515ad1c78ec0c39, dceb62e8fa94b46006c9554fed743df0, 5f9d46795c3126674e52becb3a1a517f |
| TIM-05 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | flag | - |
| TIM-06 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | flag | - |
| TIM-07 | reviews | 99224 | 74 | 0.0746% | 0.1500% | WARN | flag | 3415c9f764e478409e8e0660ae816dd2, 49f695dffa457eaba90d388a5c37e942, 70475385a0628cbcbf6e0ba534ab69d4, 08528f70f579f0c830189efc523d2182, f1f8696d256889c0fe9962a5d32746e0 |
| TIM-08 | reviews | 99224 | 0 | 0.0000% | 0.1000% | PASS | flag | - |
| DOM-01 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | flag | - |
| DOM-02 | order_payments | 103886 | 3 | 0.0029% | 0.0100% | WARN | flag | 4637ca194b6387e2d538dc89b124b0ee#1, 00b1cb0320190ca0daa2c88b35206009#1, c8c528189310eaa44a745b8d9d26908b#1 |
| DOM-03 | order_payments | 103886 | 9 | 0.0087% | 0.0150% | WARN | flag | 8bcbe01d44d147f901cd3192671144db#4, fa65dad1b0e818e3ccc5cb0e39231352#14, 6ccb433e00daae1283ccc956189c82ae#4, 4637ca194b6387e2d538dc89b124b0ee#1, 00b1cb0320190ca0daa2c88b35206009#1 |
| DOM-04 | order_payments | 103886 | 2 | 0.0019% | 0.0100% | WARN | flag | 744bade1fcf9ff3f31d860ace076d422#2, 1a57108394169c0b47d8f876acc9ba2d#2 |
| DOM-05 | order_items | 112650 | 0 | 0.0000% | 0.0000% | PASS | quarantine | - |
| DOM-06 | reviews | 99224 | 0 | 0.0000% | 0.1000% | PASS | flag | - |
| DOM-07 | orders | 99441 | 0 | 0.0000% | 0.0000% | PASS | fix | - |
| DOM-08 | products | 32951 | 4 | 0.0121% | 0.1000% | WARN | flag | 81781c0fed9fe1ad6e8c81fca1e1cb08, 8038040ee2a71048d4bdbbdc985b69ab, 36ba42dd187055e1fbe943b2d11430ca, e673e90efa65a5409ff4196c038bb5af |
| DOM-09 | customers | 99441 | 0 | 0.0000% | 0.1000% | PASS | flag | - |
| CON-01 | orders | 98665 | 249 | 0.2524% | 0.4000% | WARN | flag | 84d6d9710c8af32b5e88f2d1c14ab871, 74016effecaa79d592487f6a4ee47d4b, 239f380355f65dcb68551f07d16fc4a8, 4c57f545143e8865ca2347d8cba154a7, 6e57e23ecac1ae881286657694444267 |
| CON-02 | orders | 96478 | 1292 | 1.3392% | 2.0000% | WARN | flag | 8563039e855156e48fccee4d611a3196, 1d067305b599c1e0dceb3864056ea527, c82a457d646f77c8f151e12a3e517ed2, 2c3a5e5f5bc3ae78ed5748461e62d47d, 6cc4eb51469dec50a6130fe1cd07b7f9 |

规则条件、查询分母、对指标的影响见 [质量规则清单](quality_rules.md)，完整SQL见 `SQL/governance/02_quality_checks.sql`。异常数按规则分别计数，同一记录可命中多条规则，不能把上述数字相加当作异常订单数。

## 3. 重点解释与处置

重复键：订单/客户/商品/卖家及明细、支付主键均无重复，评价却有814条“除首条外”的主键冲突。A的主键与源数据粒度不一致，不能未经复核断言后续评价是重复垃圾。临时隔离保存原始负载，建议A评估(review_id, order_id)联合主键。

关联失败：所有前向外键均为0异常，但775笔订单无明细、1笔无支付；INNER JOIN明细会丢掉这些订单。应保留主订单，标注无明细/无支付，而不是把金额缺失悄悄解释成真实0元。278条客户及7条卖家记录无邮编坐标，距离类分析应说明覆盖率。

条件缺失：delivered订单中8笔缺签收、14笔缺批准，shipped/delivered中2笔缺交承运；未送达状态有签收的6笔均为canceled。缺签收8笔从延迟天数分母排除，状态矛盾6笔标记而不自动改业务状态。

时间矛盾：166笔交承运早于下单、1359笔早于批准、23笔签收早于交承运；这些需要上游复核，不能简单交换日期制造“正确数据”。延迟视图附质量提示，未将所有时间标记订单自动排除。

金额核对：先对明细与支付分别按订单聚合，再比较 SUM(price+freight_value) 与 SUM(payment_value)，容差1.00下249筆异常。1.00是课堂复核阈值，不证明差异由分期利息造成；退款、优惠、截取缺失等原因尚无源字段支持。原验证脚本只比较price与payment会遗漏运费。

## 4. 履约指标口径核对

已送达且签收/预计两日期非空的有效分母：96470单。

| 口径 | 订单数 | 含义 |
|---|---:|---|
| A现有v_delayed_orders | 7827 | 所有状态且签收时刻>预计时刻 |
| 限定delivered、时刻比较 | 7826 | 去掉1笔canceled订单 |
| 限定delivered、DATEDIFF≥1 | 6534 | 同预计日期送达视为准时；治理候选口径 |
| 两种delivered口径差额 | 1292 | 预计日期当天、午夜之后签收，DATEDIFF=0 |

新视图 v_delayed_orders_governed 与 A 原视图并存；未经组长确认，不替换B现有页面口径。天数口径延迟率=6534/96470≈6.7731%，时刻口径=7826/96470≈8.1124%；平均正延迟10.6201天、最大188天。

## 5. 复现与证据

逐规则CSV：`EVIDENCE/quality_batch_20261109_223909.csv`；行数CSV：`EVIDENCE/reconciliation_batch_20261109_223909.csv`；日志CSV：`EVIDENCE/processing_batch_20261109_223909.csv`。源文件SHA-256指纹与逐单血缘证据在 `EVIDENCE/run_outputs/verified_facts.json`。

质量明细 quality_check_results 每规则最多1000条（本批6058条）；完整异常数量存汇总表。例如geo异常981148条不是只1000条。完整隔离814行存 data_quarantine；标记保存在 data_quality_flags。详见 [处置说明](disposal_instructions.md)。

覆盖边界：45条规则不构成全面数据认证；没有验证全套非法日历日期、键trim后碰撞、维表空键、子表序号格式、坐标范围及并发。安全与隐私扫描见单独验证记录。