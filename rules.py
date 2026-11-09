"""
质量规则注册表（单一来源）- 电商履约数据整合系统
负责人：组员C

说明：
    1. 每条规则对应一条返回"异常记录"的 SQL，统一输出两列：record_key（业务键）与 src_row_num（暂存层行号，
       即原始 CSV 第几条数据记录，不含表头）。规则运行在暂存层 stg_*，因此能发现核心表约束会直接拒绝的问题
       （如重复主键、关联失败）。
    2. checked_sql 给出分母（被检查的记录数），用于计算异常率 fail_rate = failed_rows / checked_rows。
    3. 判定：failed_rows = 0 -> PASS；0 < fail_rate <= threshold -> WARN；fail_rate > threshold -> FAIL。
       critical 规则阈值为 0，出现即 FAIL；warning/info 规则阈值按 2026-11-09 首次全量画像结果的约 1.5~2 倍设定，
       使"已知存量问题"为 WARN，异常放大时升级为 FAIL。
    4. disposal_action：quarantine（隔离，不进入核心表）/ flag（保留并标记）/ fix（按规则修正后进入核心表）。
    5. 依据：组员A《数据字典》《关系模式与建表说明》《来源字段及转换说明》中的主键、外键、可空与业务规则。

本文件同时被 governance_pipeline.py（执行）与 export_rules.py（导出 SQL 脚本、规则清单）使用。
"""

# ---------- SQL 片段 ----------
DT_REGEX = "'^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'"
NUM_REGEX = "'^-?[0-9]+([.][0-9]+)?$'"


def D(col):
    """把暂存层字符串安全解析为 DATETIME；格式不符或非法日期返回 NULL。"""
    return (f"(CASE WHEN TRIM({col}) REGEXP {DT_REGEX} "
            f"THEN STR_TO_DATE(TRIM({col}), '%Y-%m-%d %H:%i:%s') END)")


def N(col, typ="DECIMAL(12,2)"):
    """把暂存层字符串安全解析为数值；非数字返回 NULL。"""
    return f"(CASE WHEN TRIM({col}) REGEXP {NUM_REGEX} THEN CAST(TRIM({col}) AS {typ}) END)"


def E(col):
    """空值判断：NULL 或空白字符串。"""
    return f"(NULLIF(TRIM({col}), '') IS NULL)"


def dup_rule(table, key_cols):
    """重复键：返回同一业务键除首条（最小 src_row_num）以外的其余记录。"""
    stg = f"stg_{table}"
    if len(key_cols) == 1:
        key_expr = f"s.{key_cols[0]}"
    else:
        key_expr = "CONCAT(" + ", '#', ".join(f"s.{c}" for c in key_cols) + ")"
    join_cond = " AND ".join(f"s.{c} = d.{c}" for c in key_cols)
    cols = ", ".join(key_cols)
    return (f"SELECT {key_expr} AS record_key, s.src_row_num FROM {stg} s "
            f"JOIN (SELECT {cols}, MIN(src_row_num) AS first_row FROM {stg} GROUP BY {cols} HAVING COUNT(*) > 1) d "
            f"ON {join_cond} AND s.src_row_num > d.first_row")


ITEM_KEY = "CONCAT(i.order_id, '#', i.order_item_id)"
PAY_KEY = "CONCAT(p.order_id, '#', p.payment_sequential)"

ORDER_STATUS_DOMAIN = "('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved')"
PAYMENT_TYPE_DOMAIN = "('credit_card','boleto','voucher','debit_card')"

RULES = [
    # ======================= 1. 重复键 =======================
    dict(rule_id="DUP-01", rule_name="订单号重复", category="重复键", table="orders", columns="order_id",
         description="orders.order_id 为主键，同一 order_id 出现多行时，除首行外其余行判为重复。",
         sql=dup_rule("orders", ["order_id"]), checked="SELECT COUNT(*) FROM stg_orders",
         severity="critical", threshold=0, action="quarantine",
         impact="订单数、延迟订单数被重复计数；核心表主键冲突导致导入失败"),
    dict(rule_id="DUP-02", rule_name="客户ID重复", category="重复键", table="customers", columns="customer_id",
         description="customers.customer_id 为主键，重复时除首行外隔离。",
         sql=dup_rule("customers", ["customer_id"]), checked="SELECT COUNT(*) FROM stg_customers",
         severity="critical", threshold=0, action="quarantine", impact="客户维度关联放大订单行"),
    dict(rule_id="DUP-03", rule_name="订单明细联合主键重复", category="重复键", table="order_items",
         columns="order_id, order_item_id",
         description="(order_id, order_item_id) 为联合主键，重复时除首行外隔离。",
         sql=dup_rule("order_items", ["order_id", "order_item_id"]), checked="SELECT COUNT(*) FROM stg_order_items",
         severity="critical", threshold=0, action="quarantine", impact="商品金额 SUM(price) 被放大"),
    dict(rule_id="DUP-04", rule_name="支付记录联合主键重复", category="重复键", table="order_payments",
         columns="order_id, payment_sequential",
         description="(order_id, payment_sequential) 为联合主键，重复时除首行外隔离。",
         sql=dup_rule("order_payments", ["order_id", "payment_sequential"]),
         checked="SELECT COUNT(*) FROM stg_order_payments",
         severity="critical", threshold=0, action="quarantine", impact="支付总额 SUM(payment_value) 被放大"),
    dict(rule_id="DUP-05", rule_name="评价ID对应多个订单", category="重复键", table="reviews", columns="review_id",
         description="A 的模型以 review_id 为主键，但源数据中同一 review_id 关联多个 order_id。"
                     "为满足主键约束，除首行外隔离并保留原始负载，建议 A 将主键改为 (review_id, order_id)。",
         sql=dup_rule("reviews", ["review_id"]), checked="SELECT COUNT(*) FROM stg_reviews",
         severity="warning", threshold=0.015, action="quarantine",
         impact="被隔离的订单缺少评价，评分类指标覆盖率下降"),
    dict(rule_id="DUP-06", rule_name="商品ID重复", category="重复键", table="products", columns="product_id",
         description="products.product_id 为主键，重复时除首行外隔离。",
         sql=dup_rule("products", ["product_id"]), checked="SELECT COUNT(*) FROM stg_products",
         severity="critical", threshold=0, action="quarantine", impact="品类分布统计放大"),
    dict(rule_id="DUP-07", rule_name="卖家ID重复", category="重复键", table="sellers", columns="seller_id",
         description="sellers.seller_id 为主键，重复时除首行外隔离。",
         sql=dup_rule("sellers", ["seller_id"]), checked="SELECT COUNT(*) FROM stg_sellers",
         severity="critical", threshold=0, action="quarantine", impact="卖家绩效统计放大"),
    dict(rule_id="DUP-08", rule_name="邮编前缀多坐标", category="重复键", table="geolocation",
         columns="geolocation_zip_code_prefix",
         description="A 的模型以邮编前缀为主键，但源文件中一个前缀对应多行坐标。处置为修正：按前缀聚合，"
                     "经纬度取平均值、城市/州取首行，而不是像原导入脚本那样静默保留首行。",
         sql=dup_rule("geolocation", ["geolocation_zip_code_prefix"]), checked="SELECT COUNT(*) FROM stg_geolocation",
         severity="info", threshold=1.0, action="fix", impact="若直接关联会使客户/卖家行数膨胀"),

    # ======================= 2. 关联失败 =======================
    dict(rule_id="REF-01", rule_name="明细找不到订单", category="关联失败", table="order_items", columns="order_id",
         description="order_items.order_id 必须存在于 orders。",
         sql=f"SELECT {ITEM_KEY} AS record_key, i.src_row_num FROM stg_order_items i "
             f"LEFT JOIN stg_orders o ON o.order_id = i.order_id WHERE o.order_id IS NULL",
         checked="SELECT COUNT(*) FROM stg_order_items", severity="critical", threshold=0, action="quarantine",
         impact="孤立明细使商品金额无法归属订单，FK 约束导致导入失败"),
    dict(rule_id="REF-02", rule_name="明细找不到商品", category="关联失败", table="order_items", columns="product_id",
         description="order_items.product_id 必须存在于 products。",
         sql=f"SELECT {ITEM_KEY} AS record_key, i.src_row_num FROM stg_order_items i "
             f"LEFT JOIN stg_products p ON p.product_id = i.product_id WHERE p.product_id IS NULL",
         checked="SELECT COUNT(*) FROM stg_order_items", severity="critical", threshold=0, action="quarantine",
         impact="品类维度统计缺失"),
    dict(rule_id="REF-03", rule_name="明细找不到卖家", category="关联失败", table="order_items", columns="seller_id",
         description="order_items.seller_id 必须存在于 sellers。",
         sql=f"SELECT {ITEM_KEY} AS record_key, i.src_row_num FROM stg_order_items i "
             f"LEFT JOIN stg_sellers s ON s.seller_id = i.seller_id WHERE s.seller_id IS NULL",
         checked="SELECT COUNT(*) FROM stg_order_items", severity="critical", threshold=0, action="quarantine",
         impact="卖家绩效统计缺失"),
    dict(rule_id="REF-04", rule_name="支付找不到订单", category="关联失败", table="order_payments", columns="order_id",
         description="order_payments.order_id 必须存在于 orders。",
         sql=f"SELECT {PAY_KEY} AS record_key, p.src_row_num FROM stg_order_payments p "
             f"LEFT JOIN stg_orders o ON o.order_id = p.order_id WHERE o.order_id IS NULL",
         checked="SELECT COUNT(*) FROM stg_order_payments", severity="critical", threshold=0, action="quarantine",
         impact="支付金额无法归属订单"),
    dict(rule_id="REF-05", rule_name="评价找不到订单", category="关联失败", table="reviews", columns="order_id",
         description="reviews.order_id 必须存在于 orders。",
         sql="SELECT r.review_id AS record_key, r.src_row_num FROM stg_reviews r "
             "LEFT JOIN stg_orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL",
         checked="SELECT COUNT(*) FROM stg_reviews", severity="critical", threshold=0, action="quarantine",
         impact="评价无法归属订单"),
    dict(rule_id="REF-06", rule_name="订单找不到客户", category="关联失败", table="orders", columns="customer_id",
         description="orders.customer_id 必须存在于 customers。",
         sql="SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o "
             "LEFT JOIN stg_customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL",
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="quarantine",
         impact="按州/城市的延迟率无法计算；其明细与支付级联隔离"),
    dict(rule_id="REF-07", rule_name="订单没有任何明细", category="关联失败", table="orders", columns="order_id",
         description="反向关联：orders 中存在但 order_items 中没有明细的订单。",
         sql="SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o "
             "WHERE NOT EXISTS (SELECT 1 FROM stg_order_items i WHERE i.order_id = o.order_id)",
         checked="SELECT COUNT(*) FROM stg_orders", severity="warning", threshold=0.012, action="flag",
         impact="v_order_fulfillment 使用 INNER JOIN 会丢失这些订单；订单金额显示为 0"),
    dict(rule_id="REF-08", rule_name="订单没有支付记录", category="关联失败", table="orders", columns="order_id",
         description="反向关联：orders 中存在但 order_payments 中没有记录的订单。",
         sql="SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o "
             "WHERE NOT EXISTS (SELECT 1 FROM stg_order_payments p WHERE p.order_id = o.order_id)",
         checked="SELECT COUNT(*) FROM stg_orders", severity="warning", threshold=0.0005, action="flag",
         impact="支付总额为 0，金额核对失败"),
    dict(rule_id="REF-09", rule_name="客户邮编无坐标", category="关联失败", table="customers",
         columns="customer_zip_code_prefix",
         description="customers.customer_zip_code_prefix 在 geolocation 中找不到。",
         sql="SELECT c.customer_id AS record_key, c.src_row_num FROM stg_customers c "
             "WHERE NOT EXISTS (SELECT 1 FROM stg_geolocation g "
             "WHERE g.geolocation_zip_code_prefix = c.customer_zip_code_prefix)",
         checked="SELECT COUNT(*) FROM stg_customers", severity="info", threshold=0.005, action="flag",
         impact="距离类分析需使用 LEFT JOIN 并接受缺失"),
    dict(rule_id="REF-10", rule_name="卖家邮编无坐标", category="关联失败", table="sellers",
         columns="seller_zip_code_prefix",
         description="sellers.seller_zip_code_prefix 在 geolocation 中找不到。",
         sql="SELECT s.seller_id AS record_key, s.src_row_num FROM stg_sellers s "
             "WHERE NOT EXISTS (SELECT 1 FROM stg_geolocation g "
             "WHERE g.geolocation_zip_code_prefix = s.seller_zip_code_prefix)",
         checked="SELECT COUNT(*) FROM stg_sellers", severity="info", threshold=0.005, action="flag",
         impact="卖家-客户距离无法计算"),
    dict(rule_id="REF-11", rule_name="品类无英文翻译", category="关联失败", table="products",
         columns="product_category_name",
         description="非空品类名在 product_category_name_translation 中找不到对应英文名。",
         sql="SELECT p.product_id AS record_key, p.src_row_num FROM stg_products p "
             "WHERE NULLIF(TRIM(p.product_category_name), '') IS NOT NULL AND NOT EXISTS "
             "(SELECT 1 FROM stg_category_translation t WHERE t.product_category_name = p.product_category_name)",
         checked="SELECT COUNT(*) FROM stg_products", severity="info", threshold=0.005, action="flag",
         impact="英文品类展示为空"),

    # ======================= 3. 条件缺失 =======================
    dict(rule_id="NUL-01", rule_name="已送达但缺签收时间", category="条件缺失", table="orders",
         columns="order_status, order_delivered_customer_date",
         description="order_status = 'delivered' 时 order_delivered_customer_date 不应为空。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE LOWER(TRIM(order_status)) = 'delivered' AND {E('order_delivered_customer_date')}",
         checked="SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered'",
         severity="warning", threshold=0.00015, action="flag",
         impact="延迟天数无法计算，被统一口径排除，延迟率分母减少"),
    dict(rule_id="NUL-02", rule_name="已送达但缺支付批准时间", category="条件缺失", table="orders",
         columns="order_status, order_approved_at",
         description="order_status = 'delivered' 时 order_approved_at 不应为空。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE LOWER(TRIM(order_status)) = 'delivered' AND {E('order_approved_at')}",
         checked="SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered'",
         severity="warning", threshold=0.0003, action="flag", impact="卖家发货时长无法计算"),
    dict(rule_id="NUL-03", rule_name="已发货/送达但缺承运时间", category="条件缺失", table="orders",
         columns="order_status, order_delivered_carrier_date",
         description="order_status IN ('shipped','delivered') 时 order_delivered_carrier_date 不应为空。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE LOWER(TRIM(order_status)) IN ('shipped','delivered') AND {E('order_delivered_carrier_date')}",
         checked="SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) IN ('shipped','delivered')",
         severity="warning", threshold=0.0001, action="flag", impact="物流时长无法计算"),
    dict(rule_id="NUL-04", rule_name="未送达状态却有签收时间", category="条件缺失", table="orders",
         columns="order_status, order_delivered_customer_date",
         description="order_status <> 'delivered' 时出现 order_delivered_customer_date，状态与时间戳矛盾。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE LOWER(TRIM(order_status)) <> 'delivered' AND NOT {E('order_delivered_customer_date')}",
         checked="SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) <> 'delivered'",
         severity="warning", threshold=0.004, action="flag",
         impact="A 的 v_delayed_orders 未限定状态，会把此类订单计入延迟（7827 vs 7826 差异来源）"),
    dict(rule_id="NUL-05", rule_name="缺预计送达日期", category="条件缺失", table="orders",
         columns="order_estimated_delivery_date",
         description="order_estimated_delivery_date 为延迟天数的必需输入，不应为空。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE {E('order_estimated_delivery_date')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="flag",
         impact="延迟天数无法计算"),
    dict(rule_id="NUL-06", rule_name="订单关键字段为空", category="条件缺失", table="orders",
         columns="order_id, customer_id, order_purchase_timestamp",
         description="order_id、customer_id、order_purchase_timestamp 为 NOT NULL 关键字段。",
         sql=f"SELECT COALESCE(NULLIF(TRIM(order_id), ''), CONCAT('row#', src_row_num)) AS record_key, src_row_num "
             f"FROM stg_orders WHERE {E('order_id')} OR {E('customer_id')} OR {E('order_purchase_timestamp')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="quarantine",
         impact="无法定位订单或无法按时间范围统计"),
    dict(rule_id="NUL-07", rule_name="商品品类为空", category="条件缺失", table="products",
         columns="product_category_name",
         description="product_category_name 为空，品类分布中归入'未知'。",
         sql=f"SELECT product_id AS record_key, src_row_num FROM stg_products WHERE {E('product_category_name')}",
         checked="SELECT COUNT(*) FROM stg_products", severity="info", threshold=0.03, action="flag",
         impact="延迟订单品类分布中出现'未知'品类"),

    # ======================= 4. 时间顺序矛盾 =======================
    dict(rule_id="TIM-01", rule_name="批准早于下单", category="时间顺序", table="orders",
         columns="order_approved_at, order_purchase_timestamp",
         description="order_approved_at >= order_purchase_timestamp（A 数据字典业务规则）。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE {D('order_approved_at')} < {D('order_purchase_timestamp')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="warning", threshold=0.001, action="flag",
         impact="卖家处理时长为负"),
    dict(rule_id="TIM-02", rule_name="交承运早于下单", category="时间顺序", table="orders",
         columns="order_delivered_carrier_date, order_purchase_timestamp",
         description="order_delivered_carrier_date 不应早于 order_purchase_timestamp。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE {D('order_delivered_carrier_date')} < {D('order_purchase_timestamp')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="warning", threshold=0.0025, action="flag",
         impact="物流时长、履约时长分解失真"),
    dict(rule_id="TIM-03", rule_name="交承运早于支付批准", category="时间顺序", table="orders",
         columns="order_delivered_carrier_date, order_approved_at",
         description="order_delivered_carrier_date >= order_approved_at（A 关系模式一般化约束）。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE {D('order_delivered_carrier_date')} < {D('order_approved_at')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="info", threshold=0.02, action="flag",
         impact="卖家发货时长为负，可能是批准时间回写延迟"),
    dict(rule_id="TIM-04", rule_name="签收早于交承运", category="时间顺序", table="orders",
         columns="order_delivered_customer_date, order_delivered_carrier_date",
         description="order_delivered_customer_date >= order_delivered_carrier_date（A 数据字典业务规则）。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE {D('order_delivered_customer_date')} < {D('order_delivered_carrier_date')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="warning", threshold=0.0004, action="flag",
         impact="签收时间可疑，相关订单的延迟天数可信度降低（页面以标记提示）"),
    dict(rule_id="TIM-05", rule_name="签收早于下单", category="时间顺序", table="orders",
         columns="order_delivered_customer_date, order_purchase_timestamp",
         description="order_delivered_customer_date 不得早于 order_purchase_timestamp。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE {D('order_delivered_customer_date')} < {D('order_purchase_timestamp')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="flag",
         impact="履约时长为负，延迟天数不可信"),
    dict(rule_id="TIM-06", rule_name="预计送达早于下单", category="时间顺序", table="orders",
         columns="order_estimated_delivery_date, order_purchase_timestamp",
         description="order_estimated_delivery_date 不得早于 order_purchase_timestamp。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE {D('order_estimated_delivery_date')} < {D('order_purchase_timestamp')}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="flag",
         impact="延迟天数被系统性放大"),
    dict(rule_id="TIM-07", rule_name="评价早于下单", category="时间顺序", table="reviews",
         columns="review_creation_date, orders.order_purchase_timestamp",
         description="review_creation_date 不应早于对应订单的下单时间。",
         sql=f"SELECT r.review_id AS record_key, r.src_row_num FROM stg_reviews r "
             f"JOIN stg_orders o ON o.order_id = r.order_id "
             f"WHERE {D('r.review_creation_date')} < {D('o.order_purchase_timestamp')}",
         checked="SELECT COUNT(*) FROM stg_reviews", severity="info", threshold=0.0015, action="flag",
         impact="评价与订单关联可疑"),
    dict(rule_id="TIM-08", rule_name="回复早于评价", category="时间顺序", table="reviews",
         columns="review_answer_timestamp, review_creation_date",
         description="review_answer_timestamp 不应早于 review_creation_date。",
         sql=f"SELECT review_id AS record_key, src_row_num FROM stg_reviews "
             f"WHERE {D('review_answer_timestamp')} < {D('review_creation_date')}",
         checked="SELECT COUNT(*) FROM stg_reviews", severity="warning", threshold=0.001, action="flag",
         impact="回复时长为负"),

    # ======================= 5. 域值与范围 =======================
    dict(rule_id="DOM-01", rule_name="订单状态不在域内", category="域值范围", table="orders", columns="order_status",
         description=f"order_status 取值应属于实际业务域 {ORDER_STATUS_DOMAIN}（已按源数据修订 A 的域约束）。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE LOWER(TRIM(COALESCE(order_status, ''))) NOT IN {ORDER_STATUS_DOMAIN}",
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="flag",
         impact="按状态筛选（如 delivered）的指标漏算"),
    dict(rule_id="DOM-02", rule_name="支付方式不在域内", category="域值范围", table="order_payments",
         columns="payment_type",
         description=f"payment_type 应属于 {PAYMENT_TYPE_DOMAIN}。",
         sql=f"SELECT {PAY_KEY} AS record_key, p.src_row_num FROM stg_order_payments p "
             f"WHERE LOWER(TRIM(COALESCE(p.payment_type, ''))) NOT IN {PAYMENT_TYPE_DOMAIN}",
         checked="SELECT COUNT(*) FROM stg_order_payments", severity="warning", threshold=0.0001, action="flag",
         impact="支付方式分布出现未定义类别"),
    dict(rule_id="DOM-03", rule_name="支付金额非正", category="域值范围", table="order_payments",
         columns="payment_value",
         description="payment_value > 0（A 域约束）；无法解析为数字也视为异常。",
         sql=f"SELECT {PAY_KEY} AS record_key, p.src_row_num FROM stg_order_payments p "
             f"WHERE {N('p.payment_value')} IS NULL OR {N('p.payment_value')} <= 0",
         checked="SELECT COUNT(*) FROM stg_order_payments", severity="warning", threshold=0.00015, action="flag",
         impact="支付总额与商品金额核对失败"),
    dict(rule_id="DOM-04", rule_name="分期数小于1", category="域值范围", table="order_payments",
         columns="payment_installments",
         description="payment_installments >= 1（A 域约束）。",
         sql=f"SELECT {PAY_KEY} AS record_key, p.src_row_num FROM stg_order_payments p "
             f"WHERE {N('p.payment_installments', 'SIGNED')} IS NULL OR {N('p.payment_installments', 'SIGNED')} < 1",
         checked="SELECT COUNT(*) FROM stg_order_payments", severity="warning", threshold=0.0001, action="flag",
         impact="分期分析出现 0 期"),
    dict(rule_id="DOM-05", rule_name="商品价格/运费非法", category="域值范围", table="order_items",
         columns="price, freight_value",
         description="price > 0 且 freight_value >= 0，且均可解析为数字（核心表为 NOT NULL DECIMAL）。",
         sql=f"SELECT {ITEM_KEY} AS record_key, i.src_row_num FROM stg_order_items i "
             f"WHERE {N('i.price')} IS NULL OR {N('i.price')} <= 0 "
             f"OR {N('i.freight_value')} IS NULL OR {N('i.freight_value')} < 0",
         checked="SELECT COUNT(*) FROM stg_order_items", severity="critical", threshold=0, action="quarantine",
         impact="订单金额错误，无法写入 NOT NULL 金额字段"),
    dict(rule_id="DOM-06", rule_name="评分不在1-5", category="域值范围", table="reviews", columns="review_score",
         description="review_score ∈ {1,2,3,4,5}。",
         sql=f"SELECT review_id AS record_key, src_row_num FROM stg_reviews "
             f"WHERE TRIM(COALESCE(review_score, '')) NOT IN ('1','2','3','4','5')",
         checked="SELECT COUNT(*) FROM stg_reviews", severity="warning", threshold=0.001, action="flag",
         impact="平均评分失真"),
    dict(rule_id="DOM-07", rule_name="订单时间戳无法解析", category="域值范围", table="orders",
         columns="order_purchase_timestamp ... order_estimated_delivery_date",
         description="非空时间戳必须符合 'YYYY-MM-DD HH:MM:SS' 且为合法日期；否则修正为 NULL 并标记，"
                     "避免像 pandas errors='coerce' 那样静默变成空值。",
         sql="SELECT order_id AS record_key, src_row_num FROM stg_orders WHERE " + " OR ".join(
             f"(NOT {E(c)} AND {D(c)} IS NULL)" for c in [
                 "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                 "order_delivered_customer_date", "order_estimated_delivery_date"]),
         checked="SELECT COUNT(*) FROM stg_orders", severity="critical", threshold=0, action="fix",
         impact="延迟天数等时间指标静默缺失"),
    dict(rule_id="DOM-08", rule_name="商品重量/尺寸非正", category="域值范围", table="products",
         columns="product_weight_g, product_length_cm, product_height_cm, product_width_cm",
         description="非空的重量与尺寸应 > 0。",
         sql=f"SELECT product_id AS record_key, src_row_num FROM stg_products WHERE "
             + " OR ".join(f"{N(c, 'SIGNED')} <= 0" for c in
                           ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]),
         checked="SELECT COUNT(*) FROM stg_products", severity="info", threshold=0.001, action="flag",
         impact="运费/体积分析异常"),
    dict(rule_id="DOM-09", rule_name="州代码格式错误", category="域值范围", table="customers", columns="customer_state",
         description="customer_state 应为两位大写字母（如 SP、RJ）。",
         sql="SELECT customer_id AS record_key, src_row_num FROM stg_customers "
             "WHERE NOT REGEXP_LIKE(TRIM(COALESCE(customer_state, '')), '^[A-Z]{2}$', 'c')",
         checked="SELECT COUNT(*) FROM stg_customers", severity="warning", threshold=0.001, action="flag",
         impact="按州延迟率统计出现异常分组"),

    # ======================= 6. 一致性 / 指标口径 =======================
    dict(rule_id="CON-01", rule_name="支付总额与商品+运费不符", category="一致性", table="orders",
         columns="SUM(payment_value) vs SUM(price+freight_value)",
         description="同一订单 |SUM(payment_value) - SUM(price + freight_value)| > 1.00 视为金额不一致"
                     "（分期利息、优惠券可造成小额差异，故容差取 1.00）。",
         sql="SELECT o.order_id AS record_key, o.src_row_num FROM stg_orders o "
             f"JOIN (SELECT order_id, SUM({N('price')} + {N('freight_value')}) AS amt FROM stg_order_items GROUP BY order_id) i "
             "ON i.order_id = o.order_id "
             f"JOIN (SELECT order_id, SUM({N('payment_value')}) AS paid FROM stg_order_payments GROUP BY order_id) p "
             "ON p.order_id = o.order_id WHERE ABS(p.paid - i.amt) > 1.00",
         checked="SELECT COUNT(*) FROM stg_orders o WHERE EXISTS (SELECT 1 FROM stg_order_items i WHERE i.order_id=o.order_id) "
                 "AND EXISTS (SELECT 1 FROM stg_order_payments p WHERE p.order_id=o.order_id)",
         severity="warning", threshold=0.004, action="flag", impact="订单金额展示与支付对账不一致"),
    dict(rule_id="CON-02", rule_name="晚于预计时刻但延迟天数为0", category="口径", table="orders",
         columns="order_delivered_customer_date, order_estimated_delivery_date",
         description="已送达订单签收时间 > 预计送达时间（预计时间均为 00:00:00），但 DATEDIFF = 0（当天签收）。"
                     "'实际 > 预计' 与 '延迟天数 > 0' 两种口径对这些订单结论相反，需组长确认统一口径。",
         sql=f"SELECT order_id AS record_key, src_row_num FROM stg_orders "
             f"WHERE LOWER(TRIM(order_status)) = 'delivered' "
             f"AND {D('order_delivered_customer_date')} > {D('order_estimated_delivery_date')} "
             f"AND DATEDIFF({D('order_delivered_customer_date')}, {D('order_estimated_delivery_date')}) = 0",
         checked="SELECT COUNT(*) FROM stg_orders WHERE LOWER(TRIM(order_status)) = 'delivered'",
         severity="info", threshold=0.02, action="flag",
         impact="延迟订单数在 7826（时刻口径）与 6534（天数口径）之间摇摆"),
]

RULE_INDEX = {r["rule_id"]: r for r in RULES}

if __name__ == "__main__":
    from collections import Counter
    print(len(RULES), "rules")
    print(Counter(r["category"] for r in RULES))
    print(Counter(r["action"] for r in RULES))
