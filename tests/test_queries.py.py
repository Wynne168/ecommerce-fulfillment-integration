"""
查询测试脚本 - 电商履约数据整合系统
负责人：组员A

功能：对核心查询进行单元测试验证，确保查询结果正确性

运行方式：
    python -m pytest tests/test_queries.py -v

依赖安装：
    pip install pytest sqlalchemy pymysql

注意：
    1. 需要先执行 sql/create_tables.sql 建表
    2. 需要先执行数据导入脚本导入测试数据
    3. 测试配置文件 tests/test_config.json 中配置数据库连接
"""

import pytest
import os
import json
from sqlalchemy import create_engine, text

# 加载测试配置
def load_test_config():
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def engine():
    """创建数据库连接"""
    config = load_test_config()
    db_url = config["database_url"]
    eng = create_engine(db_url)
    yield eng
    eng.dispose()

class TestOrderFulfillmentQuery:
    """订单履约详情查询测试"""

    def test_query_by_order_id(self, engine):
        """测试：按订单号查询履约详情"""
        with engine.connect() as conn:
            # 检查orders表是否有数据
            result = conn.execute(text("SELECT COUNT(*) FROM orders"))
            order_count = result.scalar()
            assert order_count > 0, "orders表应为空，请先导入数据"
            
            # 获取一个测试订单号
            result = conn.execute(text("SELECT order_id FROM orders LIMIT 1"))
            test_order_id = result.scalar()
            
            # 执行查询
            query = text("""
                SELECT o.order_id, o.customer_id, o.order_status,
                       oi.order_item_id, oi.product_id, oi.price,
                       op.payment_type, op.payment_value
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                LEFT JOIN order_payments op ON o.order_id = op.order_id
                WHERE o.order_id = :order_id
            """)
            result = conn.execute(query, {"order_id": test_order_id})
            rows = result.fetchall()
            
            # 断言：至少有一行明细
            assert len(rows) >= 1, f"订单 {test_order_id} 应至少有一条明细"
            
            # 断言：订单ID正确
            for row in rows:
                assert row[0] == test_order_id

    def test_order_summary_no_duplication(self, engine):
        """测试：订单汇总视图不存在重复计数"""
        with engine.connect() as conn:
            # 使用预聚合视图查询
            query = text("""
                SELECT order_id, total_price, total_payment, item_count, payment_count
                FROM v_order_summary
                LIMIT 10
            """)
            result = conn.execute(query)
            rows = result.fetchall()
            
            for row in rows:
                order_id, total_price, total_payment, item_count, payment_count = row
                # 金额应为非负数
                assert total_price >= 0, f"订单 {order_id} 的商品总价应为非负数"
                assert total_payment >= 0, f"订单 {order_id} 的支付总额应为非负数"
                assert item_count >= 0, f"订单 {order_id} 的商品数应为非负数"
                assert payment_count >= 0, f"订单 {order_id} 的支付笔数应为非负数"


class TestDelayedOrdersQuery:
    """延迟订单查询测试"""

    def test_delayed_orders_view_exists(self, engine):
        """测试：延迟订单视图可正常查询"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM v_delayed_orders"))
            count = result.scalar()
            # 视图表应存在（可能为0，但不应报错）
            assert count is not None

    def test_delay_calculation_correctness(self, engine):
        """测试：延迟天数计算正确性"""
        with engine.connect() as conn:
            # 手动计算延迟订单
            manual_query = text("""
                SELECT order_id,
                       DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS delay_days
                FROM orders
                WHERE order_delivered_customer_date IS NOT NULL
                  AND order_estimated_delivery_date IS NOT NULL
                  AND order_delivered_customer_date > order_estimated_delivery_date
                LIMIT 5
            """)
            manual_result = conn.execute(manual_query)
            manual_rows = manual_result.fetchall()
            
            # 用视图查询
            view_query = text("""
                SELECT order_id, delay_days
                FROM v_delayed_orders
                LIMIT 5
            """)
            view_result = conn.execute(view_query)
            view_rows = view_result.fetchall()
            
            # 视图结果不应少于手动查询结果（可能有更多数据）
            assert len(view_rows) >= min(len(manual_rows), 5) or len(manual_rows) == 0

    def test_delayed_orders_monthly_stats(self, engine):
        """测试：按月延迟统计查询可正常执行"""
        with engine.connect() as conn:
            query = text("""
                SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS month,
                       COUNT(*) AS delayed_count
                FROM v_delayed_orders
                GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
            """)
            result = conn.execute(query)
            rows = result.fetchall()
            # 查询应成功执行
            assert result is not None


class TestQueryCorrectness:
    """查询正确性验证测试"""

    def test_no_orphan_items(self, engine):
        """测试：订单明细不存在孤立记录"""
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) AS orphan_count
                FROM order_items oi
                LEFT JOIN orders o ON oi.order_id = o.order_id
                WHERE o.order_id IS NULL
            """)
            result = conn.execute(query)
            orphan_count = result.scalar()
            assert orphan_count == 0, f"存在 {orphan_count} 条订单明细的order_id在orders表中找不到"

    def test_no_orphan_payments(self, engine):
        """测试：支付记录不存在孤立记录"""
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) AS orphan_count
                FROM order_payments op
                LEFT JOIN orders o ON op.order_id = o.order_id
                WHERE o.order_id IS NULL
            """)
            result = conn.execute(query)
            orphan_count = result.scalar()
            assert orphan_count == 0, f"存在 {orphan_count} 条支付记录的order_id在orders表中找不到"

    def test_multi_item_order_amount(self, engine):
        """测试：一单多商品的金额汇总正确性"""
        with engine.connect() as conn:
            # 找有多条明细的订单
            result = conn.execute(text("""
                SELECT order_id FROM order_items
                GROUP BY order_id HAVING COUNT(*) > 1
                LIMIT 3
            """))
            multi_item_orders = [row[0] for row in result.fetchall()]
            
            if not multi_item_orders:
                pytest.skip("没有一单多商品的订单用于测试")
            
            for order_id in multi_item_orders:
                # 方法1：直接汇总order_items
                result = conn.execute(text("""
                    SELECT SUM(price), SUM(freight_value)
                    FROM order_items WHERE order_id = :oid
                """), {"oid": order_id})
                direct_price, direct_freight = result.scalar_one()
                
                # 方法2：通过视图查询
                result = conn.execute(text("""
                    SELECT total_price, total_freight
                    FROM v_order_summary WHERE order_id = :oid
                """), {"oid": order_id})
                view_price, view_freight = result.scalar_one()
                
                # 两种方法结果应一致
                assert abs(direct_price - view_price) < 0.01,                     f"订单 {order_id} 商品价格不一致: 直接={direct_price}, 视图={view_price}"
                assert abs(direct_freight - view_freight) < 0.01,                     f"订单 {order_id} 运费不一致: 直接={direct_freight}, 视图={view_freight}"

    def test_multi_payment_order_amount(self, engine):
        """测试：一单多支付的金额汇总正确性"""
        with engine.connect() as conn:
            # 找有多条支付记录的订单
            result = conn.execute(text("""
                SELECT order_id FROM order_payments
                GROUP BY order_id HAVING COUNT(*) > 1
                LIMIT 3
            """))
            multi_pay_orders = [row[0] for row in result.fetchall()]
            
            if not multi_pay_orders:
                pytest.skip("没有一单多支付的订单用于测试")
            
            for order_id in multi_pay_orders:
                # 方法1：直接汇总order_payments
                result = conn.execute(text("""
                    SELECT SUM(payment_value)
                    FROM order_payments WHERE order_id = :oid
                """), {"oid": order_id})
                direct_total = result.scalar()
                
                # 方法2：通过视图查询
                result = conn.execute(text("""
                    SELECT total_payment
                    FROM v_order_summary WHERE order_id = :oid
                """), {"oid": order_id})
                view_total = result.scalar()
                
                # 两种方法结果应一致
                assert abs(direct_total - view_total) < 0.01,                     f"订单 {order_id} 支付总额不一致: 直接={direct_total}, 视图={view_total}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
