-- ============================================
-- 治理层建表脚本：暂存层 + 质量 / 处置 / 观测 / 元数据 / 血缘
-- 负责人：组员C
-- 说明：
--   1. 本脚本只创建"治理层"对象，不修改组员A的业务表结构
--      （orders / order_items / ... / processing_log / quality_check_results 由 A 的 create_tables.sql 创建）。
--   2. 全部使用 CREATE TABLE IF NOT EXISTS，可重复执行（幂等），不会清空历史批次结果。
--   3. 暂存层 stg_* 按原样保存 CSV 字符串，并记录 batch_id / src_file / src_row_num，
--      用于"从页面结果追溯到原始 CSV 第几行"。src_row_num 为数据记录序号（不含表头，从 1 开始）。
-- 执行：mysql -u <user> -p ecommerce_fulfillment < SQL/governance/01_governance_schema.sql
-- ============================================

-- ============================================
-- A. 暂存层（Raw/Staging）：不加约束，保留原始值，便于发现重复键、关联失败等问题
-- ============================================
CREATE TABLE IF NOT EXISTS stg_orders (
    src_row_num                   INT          NOT NULL,
    batch_id                      VARCHAR(50)  NOT NULL,
    src_file                      VARCHAR(100) NOT NULL,
    order_id                      VARCHAR(255),
    customer_id                   VARCHAR(255),
    order_status                  VARCHAR(255),
    order_purchase_timestamp      VARCHAR(255),
    order_approved_at             VARCHAR(255),
    order_delivered_carrier_date  VARCHAR(255),
    order_delivered_customer_date VARCHAR(255),
    order_estimated_delivery_date VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_orders_id (order_id),
    KEY idx_stg_orders_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_order_items (
    src_row_num          INT          NOT NULL,
    batch_id             VARCHAR(50)  NOT NULL,
    src_file             VARCHAR(100) NOT NULL,
    order_id             VARCHAR(255),
    order_item_id        VARCHAR(255),
    product_id           VARCHAR(255),
    seller_id            VARCHAR(255),
    shipping_limit_date  VARCHAR(255),
    price                VARCHAR(255),
    freight_value        VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_items_order (order_id, order_item_id),
    KEY idx_stg_items_product (product_id),
    KEY idx_stg_items_seller (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_order_payments (
    src_row_num          INT          NOT NULL,
    batch_id             VARCHAR(50)  NOT NULL,
    src_file             VARCHAR(100) NOT NULL,
    order_id             VARCHAR(255),
    payment_sequential   VARCHAR(255),
    payment_type         VARCHAR(255),
    payment_installments VARCHAR(255),
    payment_value        VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_pay_order (order_id, payment_sequential)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_reviews (
    src_row_num             INT          NOT NULL,
    batch_id                VARCHAR(50)  NOT NULL,
    src_file                VARCHAR(100) NOT NULL,
    review_id               VARCHAR(255),
    order_id                VARCHAR(255),
    review_score            VARCHAR(255),
    review_comment_title    VARCHAR(500),
    review_comment_message  TEXT,
    review_creation_date    VARCHAR(255),
    review_answer_timestamp VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_rev_id (review_id),
    KEY idx_stg_rev_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_customers (
    src_row_num              INT          NOT NULL,
    batch_id                 VARCHAR(50)  NOT NULL,
    src_file                 VARCHAR(100) NOT NULL,
    customer_id              VARCHAR(255),
    customer_unique_id       VARCHAR(255),
    customer_zip_code_prefix VARCHAR(255),
    customer_city            VARCHAR(255),
    customer_state           VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_cust_id (customer_id),
    KEY idx_stg_cust_zip (customer_zip_code_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_sellers (
    src_row_num            INT          NOT NULL,
    batch_id               VARCHAR(50)  NOT NULL,
    src_file               VARCHAR(100) NOT NULL,
    seller_id              VARCHAR(255),
    seller_zip_code_prefix VARCHAR(255),
    seller_city            VARCHAR(255),
    seller_state           VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_seller_id (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_products (
    src_row_num                INT          NOT NULL,
    batch_id                   VARCHAR(50)  NOT NULL,
    src_file                   VARCHAR(100) NOT NULL,
    product_id                 VARCHAR(255),
    product_category_name      VARCHAR(255),
    product_name_lenght        VARCHAR(255),
    product_description_lenght VARCHAR(255),
    product_photos_qty         VARCHAR(255),
    product_weight_g           VARCHAR(255),
    product_length_cm          VARCHAR(255),
    product_height_cm          VARCHAR(255),
    product_width_cm           VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_prod_id (product_id),
    KEY idx_stg_prod_cat (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_geolocation (
    src_row_num                 INT          NOT NULL,
    batch_id                    VARCHAR(50)  NOT NULL,
    src_file                    VARCHAR(100) NOT NULL,
    geolocation_zip_code_prefix VARCHAR(255),
    geolocation_lat             VARCHAR(255),
    geolocation_lng             VARCHAR(255),
    geolocation_city            VARCHAR(255),
    geolocation_state           VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_geo_zip (geolocation_zip_code_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_category_translation (
    src_row_num                   INT          NOT NULL,
    batch_id                      VARCHAR(50)  NOT NULL,
    src_file                      VARCHAR(100) NOT NULL,
    product_category_name         VARCHAR(255),
    product_category_name_english VARCHAR(255),
    PRIMARY KEY (src_row_num),
    KEY idx_stg_cat (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- B. 质量规则注册表与批次检查汇总
--    明细异常记录写入 A 定义的 quality_check_results（check_name = rule_id）
-- ============================================
CREATE TABLE IF NOT EXISTS quality_rules (
    rule_id          VARCHAR(20)   NOT NULL,
    rule_name        VARCHAR(100)  NOT NULL,
    category         VARCHAR(30)   NOT NULL COMMENT '重复键/关联失败/条件缺失/时间顺序/域值范围/一致性/口径',
    table_name       VARCHAR(50)   NOT NULL,
    column_names     VARCHAR(255)  NOT NULL,
    description      TEXT          NOT NULL,
    check_sql        TEXT          NOT NULL COMMENT '返回异常记录 (record_key, src_row_num) 的 SQL',
    severity         VARCHAR(10)   NOT NULL COMMENT 'critical/warning/info',
    threshold_rate   DECIMAL(9,6)  NOT NULL DEFAULT 0 COMMENT '允许的异常率上限，超过判 FAIL',
    disposal_action  VARCHAR(20)   NOT NULL COMMENT 'quarantine/flag/fix/report',
    metric_impact    VARCHAR(255)  DEFAULT NULL,
    owner            VARCHAR(20)   NOT NULL DEFAULT '组员C',
    rule_version     VARCHAR(10)   NOT NULL DEFAULT 'v1.0',
    is_active        TINYINT       NOT NULL DEFAULT 1,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS quality_check_summary (
    summary_id          INT AUTO_INCREMENT NOT NULL,
    batch_id            VARCHAR(50)   NOT NULL,
    rule_id             VARCHAR(20)   NOT NULL,
    table_name          VARCHAR(50)   NOT NULL,
    checked_rows        INT           NOT NULL,
    failed_rows         INT           NOT NULL,
    fail_rate           DECIMAL(9,6)  NOT NULL,
    threshold_rate      DECIMAL(9,6)  NOT NULL,
    check_status        VARCHAR(10)   NOT NULL COMMENT 'PASS/WARN/FAIL/ERROR',
    severity            VARCHAR(10)   NOT NULL,
    disposal_action     VARCHAR(20)   NOT NULL,
    sample_keys         TEXT          DEFAULT NULL COMMENT '最多5个异常样例键',
    detail_rows_written INT           NOT NULL DEFAULT 0,
    duration_ms         INT           DEFAULT NULL,
    error_message       TEXT          DEFAULT NULL,
    checked_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (summary_id),
    KEY idx_qcs_batch (batch_id),
    KEY idx_qcs_rule (rule_id, batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- C. 处置：隔离区（quarantine）与标记（flag）
-- ============================================
CREATE TABLE IF NOT EXISTS data_quarantine (
    quarantine_id     INT AUTO_INCREMENT NOT NULL,
    batch_id          VARCHAR(50)  NOT NULL,
    rule_id           VARCHAR(20)  NOT NULL,
    table_name        VARCHAR(50)  NOT NULL,
    src_row_num       INT          NOT NULL,
    record_key        VARCHAR(255) DEFAULT NULL,
    raw_payload       JSON         DEFAULT NULL COMMENT '暂存层原始行，便于复核与回放',
    reason            VARCHAR(255) NOT NULL,
    resolution_status VARCHAR(20)  NOT NULL DEFAULT 'open' COMMENT 'open/released/discarded',
    quarantined_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at       DATETIME     DEFAULT NULL,
    resolution_note   VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (quarantine_id),
    KEY idx_q_batch_table (batch_id, table_name, src_row_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS data_quality_flags (
    flag_id      INT AUTO_INCREMENT NOT NULL,
    batch_id     VARCHAR(50)  NOT NULL,
    rule_id      VARCHAR(20)  NOT NULL,
    table_name   VARCHAR(50)  NOT NULL,
    record_key   VARCHAR(255) NOT NULL,
    src_row_num  INT          DEFAULT NULL,
    severity     VARCHAR(10)  NOT NULL,
    flagged_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (flag_id),
    KEY idx_f_lookup (table_name, record_key, batch_id),
    KEY idx_f_batch (batch_id, rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- D. 可观测性：行数守恒、观测规则、观测事件、业务时间与处理时间分开记录
-- ============================================
CREATE TABLE IF NOT EXISTS batch_row_reconciliation (
    batch_id           VARCHAR(50)  NOT NULL,
    table_name         VARCHAR(50)  NOT NULL,
    source_file        VARCHAR(100) DEFAULT NULL,
    source_rows        INT          DEFAULT NULL COMMENT 'CSV 数据行数（不含表头）',
    staged_rows        INT          DEFAULT NULL,
    quarantined_rows   INT          DEFAULT NULL,
    core_rows          INT          DEFAULT NULL,
    expected_core_rows INT          DEFAULT NULL,
    recon_status       VARCHAR(10)  DEFAULT NULL COMMENT 'OK/MISMATCH/MISSING',
    note               VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (batch_id, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS observability_rules (
    obs_rule_id     VARCHAR(20)  NOT NULL,
    category        VARCHAR(20)  NOT NULL COMMENT '运行/行数/质量/时效',
    rule_name       VARCHAR(100) NOT NULL,
    signal_source   VARCHAR(100) NOT NULL,
    condition_text  VARCHAR(500) NOT NULL,
    severity        VARCHAR(10)  NOT NULL,
    response_action VARCHAR(255) NOT NULL,
    PRIMARY KEY (obs_rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS observability_events (
    event_id       INT AUTO_INCREMENT NOT NULL,
    batch_id       VARCHAR(50)  NOT NULL,
    obs_rule_id    VARCHAR(20)  NOT NULL,
    object_name    VARCHAR(100) NOT NULL,
    metric_name    VARCHAR(100) NOT NULL,
    observed_value VARCHAR(100) DEFAULT NULL,
    expected_value VARCHAR(100) DEFAULT NULL,
    event_status   VARCHAR(10)  NOT NULL COMMENT 'OK/WARN/ALERT',
    severity       VARCHAR(10)  NOT NULL,
    message        VARCHAR(500) DEFAULT NULL,
    detected_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    KEY idx_oe_batch (batch_id, event_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 业务发生时间（订单日期）与数据处理时间（导入时间、处理状态）分别记录，互不混用
CREATE TABLE IF NOT EXISTS batch_data_time_profile (
    batch_id               VARCHAR(50) NOT NULL,
    business_time_field    VARCHAR(60) NOT NULL DEFAULT 'orders.order_purchase_timestamp',
    business_time_min      DATETIME    DEFAULT NULL,
    business_time_max      DATETIME    DEFAULT NULL,
    process_started_at     DATETIME    DEFAULT NULL,
    process_finished_at    DATETIME    DEFAULT NULL,
    process_status         VARCHAR(20) DEFAULT NULL,
    PRIMARY KEY (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- E. 元数据目录与指标血缘
-- ============================================
CREATE TABLE IF NOT EXISTS metadata_catalog (
    table_name          VARCHAR(50)  NOT NULL,
    column_name         VARCHAR(64)  NOT NULL,
    ordinal_position    INT          NOT NULL,
    data_type           VARCHAR(40)  NOT NULL,
    is_nullable         VARCHAR(3)   NOT NULL,
    key_type            VARCHAR(60)  DEFAULT NULL,
    business_definition VARCHAR(255) DEFAULT NULL COMMENT '来自组员A数据字典',
    source_file         VARCHAR(100) DEFAULT NULL,
    source_column       VARCHAR(100) DEFAULT NULL,
    transform_rule      VARCHAR(255) DEFAULT NULL,
    quality_requirement VARCHAR(255) DEFAULT NULL,
    quality_rule_ids    VARCHAR(255) DEFAULT NULL,
    sensitivity_level   VARCHAR(10)  DEFAULT NULL COMMENT 'L1公开/L2内部/L3敏感',
    privacy_handling    VARCHAR(255) DEFAULT NULL,
    definition_owner    VARCHAR(20)  DEFAULT '组员A',
    quality_owner       VARCHAR(20)  DEFAULT '组员C',
    null_rate           DECIMAL(9,6) DEFAULT NULL,
    distinct_count      INT          DEFAULT NULL,
    min_value           VARCHAR(100) DEFAULT NULL,
    max_value           VARCHAR(100) DEFAULT NULL,
    profiled_batch_id   VARCHAR(50)  DEFAULT NULL,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (table_name, column_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS metric_lineage (
    metric_id      VARCHAR(30)  NOT NULL,
    step_no        INT          NOT NULL,
    layer_name     VARCHAR(30)  NOT NULL COMMENT '源文件/暂存层/质量检查/核心表/指标视图/页面',
    object_name    VARCHAR(100) NOT NULL,
    field_names    VARCHAR(255) NOT NULL,
    rule_text      VARCHAR(500) NOT NULL,
    condition_text VARCHAR(500) DEFAULT NULL,
    owner          VARCHAR(20)  NOT NULL,
    PRIMARY KEY (metric_id, step_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SELECT '治理层建表完成' AS status;
