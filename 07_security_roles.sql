-- ============================================
-- 安全与隐私：角色权限、脱敏视图、卖家行级视图、强制审计过程
-- 负责人：组员C
-- 说明：
--   1. 采用"角色授权 + 视图/过程作为唯一访问路径"的最小权限设计：
--      业务角色不直接授予基表权限，只能经 SQL SECURITY DEFINER 的视图/过程访问脱敏后的数据。
--   2. MySQL 社区版没有行级安全（RLS）与审计插件，本脚本用以下方式在库内实现：
--      - 行级：v_merchant_order_items 按 USER() 与 seller_account_map 映射过滤卖家；
--      - 审计：客服只能 CALL sp_cs_lookup_order，过程先写 access_audit_log 再返回结果。
--   3. 演示用户（gov_*_demo）由 SRC/governance/security_verify.py 以随机密码临时创建、验证后删除，
--      本文件不包含任何密码。
--   4. 可重复执行。执行账号需具备 CREATE ROLE / GRANT OPTION 权限。
-- ============================================

-- ---------- 1. 审计与映射表 ----------
CREATE TABLE IF NOT EXISTS access_audit_log (
    audit_id     BIGINT AUTO_INCREMENT NOT NULL,
    db_user      VARCHAR(100) NOT NULL COMMENT 'USER()：实际登录账号',
    action       VARCHAR(50)  NOT NULL,
    object_name  VARCHAR(100) NOT NULL,
    record_key   VARCHAR(100) DEFAULT NULL,
    result_rows  INT          DEFAULT NULL,
    accessed_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    KEY idx_audit_user_time (db_user, accessed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS seller_account_map (
    db_user    VARCHAR(32) NOT NULL COMMENT '数据库账号名（不含 @host）',
    seller_id  VARCHAR(50) NOT NULL,
    granted_by VARCHAR(50) NOT NULL DEFAULT '平台管理员',
    granted_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (db_user, seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- 2. 脱敏 / 行级 / 聚合视图 ----------
-- 客服订单查询：不含 customer_id、customer_unique_id、评价原文；邮编只保留前 3 位
CREATE OR REPLACE SQL SECURITY DEFINER VIEW v_cs_order_lookup AS
SELECT o.order_id,
       o.order_status,
       o.order_purchase_timestamp,
       o.order_estimated_delivery_date,
       o.order_delivered_customer_date,
       CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
            THEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) END AS delay_days,
       c.customer_city,
       c.customer_state,
       CONCAT(LEFT(c.customer_zip_code_prefix, 3), '**') AS customer_zip_masked,
       COALESCE(i.item_count, 0)    AS item_count,
       COALESCE(i.total_price, 0)   AS total_price,
       COALESCE(i.total_freight, 0) AS total_freight,
       COALESCE(p.total_payment, 0) AS total_payment
FROM orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN (SELECT order_id, COUNT(*) AS item_count, SUM(price) AS total_price, SUM(freight_value) AS total_freight
           FROM order_items GROUP BY order_id) i ON i.order_id = o.order_id
LEFT JOIN (SELECT order_id, SUM(payment_value) AS total_payment FROM order_payments GROUP BY order_id) p
       ON p.order_id = o.order_id;

-- 商家运营：只能看到映射到本账号的卖家的明细（行级过滤），客户只显示州
CREATE OR REPLACE SQL SECURITY DEFINER VIEW v_merchant_order_items AS
SELECT oi.seller_id,
       oi.order_id,
       oi.order_item_id,
       oi.product_id,
       oi.price,
       oi.freight_value,
       oi.shipping_limit_date,
       o.order_status,
       o.order_purchase_timestamp,
       o.order_delivered_carrier_date,
       o.order_delivered_customer_date,
       o.order_estimated_delivery_date,
       c.customer_state
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE oi.seller_id IN (SELECT m.seller_id FROM seller_account_map m
                       WHERE m.db_user = SUBSTRING_INDEX(USER(), '@', 1));

-- 平台管理者：按州聚合的延迟统计；少于 10 单的分组不展示（小单元格抑制，降低再识别风险）
CREATE OR REPLACE SQL SECURITY DEFINER VIEW v_manager_delay_by_state AS
SELECT c.customer_state,
       COUNT(*)                                                                         AS delivered_orders,
       SUM(DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) >= 1) AS delayed_orders,
       ROUND(SUM(DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) >= 1) / COUNT(*), 4) AS delay_rate,
       ROUND(AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) >= 1
                      THEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) END), 2) AS avg_delay_days
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY c.customer_state
HAVING COUNT(*) >= 10;

-- 分析用评价视图：评价原文中的电话、邮箱、CPF、网址替换为占位符
CREATE OR REPLACE SQL SECURITY DEFINER VIEW v_reviews_masked AS
SELECT r.review_id,
       r.order_id,
       r.review_score,
       r.review_creation_date,
       REGEXP_REPLACE(
         REGEXP_REPLACE(
           REGEXP_REPLACE(
             REGEXP_REPLACE(COALESCE(r.review_comment_message, ''),
               '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}', '[EMAIL]'),
             '[0-9]{3}[.][0-9]{3}[.][0-9]{3}-[0-9]{2}', '[CPF]'),
           '[(]?[0-9]{2}[)]?[[:space:]]?9?[0-9]{4}[-[:space:]]?[0-9]{4}', '[PHONE]'),
         '(https?://|www[.])[^[:space:]]+', '[URL]') AS review_comment_masked
FROM reviews r;

-- ---------- 3. 审计入口约束的客服查询过程 ----------
-- 局限：日志INSERT参加调用者事务，客服在显式事务中CALL后ROLLBACK可撤销留痕。
-- 已验证自动提交场景，不可声称为不可篡改审计；生产需独立日志通道/审计插件。
-- 注意：参数显式声明排序规则。数据库默认为 utf8mb4_unicode_ci，而 A 的表只写了 DEFAULT CHARSET=utf8mb4，
--       实际为 utf8mb4_0900_ai_ci；不声明时首次验证报 ERROR 1267（见 EVIDENCE/run_outputs/security_verify_first_run_S01_collation_bug.md）
DROP PROCEDURE IF EXISTS sp_cs_lookup_order;
DELIMITER $$
CREATE DEFINER = CURRENT_USER PROCEDURE sp_cs_lookup_order(
    IN p_order_id VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_rows INT DEFAULT 0;
    SELECT COUNT(*) INTO v_rows FROM v_cs_order_lookup WHERE order_id = p_order_id;
    INSERT INTO access_audit_log (db_user, action, object_name, record_key, result_rows)
    VALUES (USER(), 'LOOKUP_ORDER', 'v_cs_order_lookup', p_order_id, v_rows);
    SELECT * FROM v_cs_order_lookup WHERE order_id = p_order_id;
END$$
DELIMITER ;

-- ---------- 4. 角色与授权（权限矩阵的可执行形式） ----------
CREATE ROLE IF NOT EXISTS role_cs_agent, role_merchant_ops, role_platform_manager,
                          role_data_governance, role_etl_runner, role_auditor;

-- 客服：只能调用审计过程（没有直接 SELECT 视图的权限，保证每次查询都留痕）
GRANT EXECUTE ON PROCEDURE sp_cs_lookup_order TO role_cs_agent;

-- 商家运营：只能查本卖家的明细视图
GRANT SELECT ON v_merchant_order_items TO role_merchant_ops;

-- 平台管理者：聚合指标 + 治理结果，不含个人级数据
GRANT SELECT ON v_manager_delay_by_state    TO role_platform_manager;
GRANT SELECT ON quality_check_summary       TO role_platform_manager;
GRANT SELECT ON observability_events        TO role_platform_manager;
GRANT SELECT ON batch_row_reconciliation    TO role_platform_manager;
GRANT SELECT ON metadata_catalog            TO role_platform_manager;
GRANT SELECT ON metric_lineage              TO role_platform_manager;

-- 数据治理（组员C）：业务表只读；治理结果表可写；不能删除业务数据；不能改审计日志
GRANT SELECT ON orders TO role_data_governance;
GRANT SELECT ON order_items TO role_data_governance;
GRANT SELECT ON order_payments TO role_data_governance;
GRANT SELECT ON customers TO role_data_governance;
GRANT SELECT ON sellers TO role_data_governance;
GRANT SELECT ON products TO role_data_governance;
GRANT SELECT ON reviews TO role_data_governance;
GRANT SELECT ON geolocation TO role_data_governance;
GRANT SELECT ON processing_log TO role_data_governance;
GRANT SELECT ON v_reviews_masked TO role_data_governance;
GRANT SELECT ON v_delayed_orders_governed TO role_data_governance;
GRANT SELECT ON v_delay_days_trace TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON quality_rules TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON quality_check_summary TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON quality_check_results TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON data_quarantine TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON data_quality_flags TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON metadata_catalog TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON metric_lineage TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON observability_rules TO role_data_governance;
GRANT SELECT, INSERT, UPDATE ON observability_events TO role_data_governance;

-- 运行账号（组员B 的处理任务）：写暂存/核心/运行记录，不授予审计日志任何权限
GRANT SELECT, INSERT, UPDATE ON processing_log TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON orders TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON order_items TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON order_payments TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON customers TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON sellers TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON products TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON reviews TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON geolocation TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_orders TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_order_items TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_order_payments TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_customers TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_sellers TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_products TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_reviews TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_geolocation TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON stg_category_translation TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE ON batch_row_reconciliation TO role_etl_runner;
GRANT SELECT, INSERT, UPDATE ON batch_data_time_profile TO role_etl_runner;

-- 审计员：只读审计日志与运行记录，看不到业务明细
GRANT SELECT ON access_audit_log     TO role_auditor;
GRANT SELECT ON processing_log       TO role_auditor;
GRANT SELECT ON observability_events TO role_auditor;

-- ---------- 5. 账号创建模板（实际由 security_verify.py 以随机密码执行） ----------
-- CREATE USER 'gov_cs_demo'@'localhost' IDENTIFIED BY '<随机密码>' PASSWORD EXPIRE INTERVAL 90 DAY FAILED_LOGIN_ATTEMPTS 5 PASSWORD_LOCK_TIME 1;
-- GRANT role_cs_agent TO 'gov_cs_demo'@'localhost';
-- SET DEFAULT ROLE ALL TO 'gov_cs_demo'@'localhost';

SELECT '安全对象与角色授权完成' AS status;
