"""
数据导入脚本 - 电商履约数据整合系统
负责人：组员A

功能：使用Python(pandas + SQLAlchemy)将Olist原始CSV数据导入MySQL数据库

使用方法：
    python src/data_import.py --config src/import_config.json

依赖安装：
    pip install pandas sqlalchemy pymysql

注意事项：
    1. 原始CSV文件需先下载至 data/raw/ 目录
    2. 数据库连接信息在 import_config.json 中配置
    3. 脚本支持幂等执行（重复运行会清空并重新导入）
    4. 大文件导入建议使用 MySQL LOAD DATA INFILE（性能更优）
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 表配置：表名 -> CSV文件名 -> 列映射
TABLE_CONFIG = {
    "customers": {
        "file": "olist_customers_dataset.csv",
        "dtype": {
            "customer_id": "str", "customer_unique_id": "str",
            "customer_zip_code_prefix": "str", "customer_city": "str", "customer_state": "str"
        },
        "date_cols": []
    },
    "sellers": {
        "file": "olist_sellers_dataset.csv",
        "dtype": {
            "seller_id": "str", "seller_zip_code_prefix": "str",
            "seller_city": "str", "seller_state": "str"
        },
        "date_cols": []
    },
    "products": {
        "file": "olist_products_dataset.csv",
        "dtype": {
            "product_id": "str", "product_category_name": "str",
            "product_name_lenght": "int64", "product_description_lenght": "int64",
            "product_photos_qty": "int64", "product_weight_g": "int64",
            "product_length_cm": "int64", "product_height_cm": "int64", "product_width_cm": "int64"
        },
        "date_cols": []
    },
    "geolocation": {
        "file": "olist_geolocation_dataset.csv",
        "dtype": {
            "geolocation_zip_code_prefix": "str", "geolocation_lat": "float64",
            "geolocation_lng": "float64", "geolocation_city": "str", "geolocation_state": "str"
        },
        "date_cols": []
    },
    "orders": {
        "file": "olist_orders_dataset.csv",
        "dtype": {
            "order_id": "str", "customer_id": "str", "order_status": "str"
        },
        "date_cols": ["order_purchase_timestamp", "order_approved_at",
                      "order_delivered_carrier_date", "order_delivered_customer_date",
                      "order_estimated_delivery_date"]
    },
    "order_items": {
        "file": "olist_order_items_dataset.csv",
        "dtype": {
            "order_id": "str", "order_item_id": "int64", "product_id": "str",
            "seller_id": "str", "price": "float64", "freight_value": "float64"
        },
        "date_cols": ["shipping_limit_date"]
    },
    "order_payments": {
        "file": "olist_order_payments_dataset.csv",
        "dtype": {
            "order_id": "str", "payment_sequential": "int64",
            "payment_type": "str", "payment_installments": "int64", "payment_value": "float64"
        },
        "date_cols": []
    },
    "reviews": {
        "file": "olist_order_reviews_dataset.csv",
        "dtype": {
            "review_id": "str", "order_id": "str", "review_score": "int64",
            "review_comment_title": "str", "review_comment_message": "str"
        },
        "date_cols": ["review_creation_date", "review_answer_timestamp"]
    }
}


def load_config(config_path="src/import_config.json"):
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def truncate_table(engine, table_name):
    """清空表数据 (导入前) """
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0")) # 临时关闭外键检查
        conn.execute(text(f"TRUNCATE TABLE {table_name}")) # 清空表
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1")) # 重新开启外键检查
    logger.info(f"已清空表: {table_name}")

def import_csv_to_table(engine, table_name, data_dir, config):
    """将CSV文件导入到数据库表"""
    csv_path = os.path.join(data_dir, config["file"])
    
    if not os.path.exists(csv_path):
        logger.warning(f"CSV文件不存在，跳过: {csv_path}")
        return 0
    
    # 读取CSV
    dtype_dict = config.get("dtype", {})
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8")
    
    # 处理日期列
    for col in config.get("date_cols", []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    # 清理字符串列的空值
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].str.strip()
    
    record_count = len(df)

        # 智能去重：如果表有主键，就按主键去重
    if 'geolocation_zip_code_prefix' in df.columns:
        df.drop_duplicates(subset=['geolocation_zip_code_prefix'], keep='first', inplace=True)
    elif 'review_id' in df.columns:
        df.drop_duplicates(subset=['review_id'], keep='first', inplace=True)
    # 写入数据库
    df.to_sql(table_name, engine, if_exists="append", index=False)
    
    logger.info(f"已导入 {record_count} 条记录到表 {table_name}")
    return record_count


def insert_batch_log(engine, batch_id, process_name, start_time, input_rows, output_rows, status, error_message=None):
    """记录处理日志"""
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO processing_log (batch_id, process_name, start_time, end_time, 
                          input_rows, output_rows, status, error_message) 
                  VALUES (:batch_id, :process_name, :start_time, :end_time, 
                          :input_rows, :output_rows, :status, :error_message)"""),
            {
                "batch_id": batch_id,
                "process_name": process_name,
                "start_time": start_time,
                "end_time": datetime.now(),
                "input_rows": input_rows,
                "output_rows": output_rows,
                "status": status,
                "error_message": error_message
            }
        )


def main():
    """主导入流程"""
    config = load_config()
    db_url = config["database_url"]
    data_dir = config.get("data_dir", "data/raw")
    
    engine = create_engine(db_url)
    start_time = datetime.now()
    batch_id = f"batch_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"开始数据导入，批次ID: {batch_id}")
    
    try:
        # 记录开始
        insert_batch_log(engine, batch_id, "import_all_data", start_time, 0, 0, "running")
        
        total_records = 0
        
        # 按依赖顺序导入（先导入被引用表）
        import_order = ["customers", "sellers", "products", "geolocation",
                        "orders", "order_items", "order_payments", "reviews"]
        
        for table_name in import_order:
            if table_name in TABLE_CONFIG:
                truncate_table(engine, table_name)
                count = import_csv_to_table(engine, table_name, data_dir, TABLE_CONFIG[table_name])
                total_records += count
        
        # 记录完成
        insert_batch_log(engine, batch_id, "import_all_data", start_time, total_records, total_records, "success")
        logger.info(f"数据导入完成，共导入 {total_records} 条记录")
        
    except Exception as e:
        logger.error(f"数据导入失败: {e}")
        insert_batch_log(engine, batch_id, "import_all_data", start_time, 0, 0, "failed", str(e))
        sys.exit(1)
    
    engine.dispose()


if __name__ == "__main__":
    main()
