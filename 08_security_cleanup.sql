-- ============================================
-- 清理安全验证的演示账号（角色与视图保留，供组内正式账号授权使用）
-- 负责人：组员C
-- ============================================
DROP USER IF EXISTS 'gov_cs_demo'@'localhost', 'gov_merchant_demo'@'localhost', 'gov_manager_demo'@'localhost',
                    'gov_governance_demo'@'localhost', 'gov_etl_demo'@'localhost', 'gov_auditor_demo'@'localhost';
DELETE FROM seller_account_map WHERE db_user = 'gov_merchant_demo';
-- 如需彻底移除角色：
-- DROP ROLE IF EXISTS role_cs_agent, role_merchant_ops, role_platform_manager, role_data_governance, role_etl_runner, role_auditor;
SELECT '演示账号已清理' AS status;
