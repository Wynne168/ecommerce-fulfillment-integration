# dataREADME.md

## 数据集来源

本项目使用 **Olist Brazilian E-Commerce Dataset**，数据来自巴西电商平台 Olist 的真实交易记录，托管于 Kaggle 平台。

- **数据集名称**：Olist Brazilian E-Commerce Dataset
- **来源平台**：Kaggle
- **数据集地址**：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **数据性质**：脱敏后的电商订单交易数据，涵盖订单、商品、支付、评价、客户、卖家、地理位置等维度
- **时间范围**：2016 年至 2018 年期间的订单数据

## 文件清单

原始数据存放于 `data/raw/` 目录下，共 9 个 CSV 文件：

| 序号  | 文件名                                     | 说明                                          |
| --- | --------------------------------------- | ------------------------------------------- |
| 1   | `olist_orders_dataset.csv`              | 订单主表，包含订单ID、客户ID、订单状态、下单时间、审批时间、发货时间、送达时间等  |
| 2   | `olist_order_items_dataset.csv`         | 订单商品明细表，包含订单ID、商品ID、卖家ID、发货邮编、商品价格、运费等      |
| 3   | `olist_order_payments_dataset.csv`      | 订单支付表，包含订单ID、支付方式、分期数、支付金额等                 |
| 4   | `olist_order_reviews_dataset.csv`       | 订单评价表，包含评价ID、订单ID、评分、评价时间、回复时间等             |
| 5   | `olist_products_dataset.csv`            | 商品表，包含商品ID、品类ID、商品名称长度、商品描述长度、商品图片数量、重量、尺寸等 |
| 6   | `olist_customers_dataset.csv`           | 客户表，包含客户ID、客户唯一ID、客户邮编、城市、州等                |
| 7   | `olist_sellers_dataset.csv`             | 卖家表，包含卖家ID、卖家邮编、城市、州等                       |
| 8   | `olist_geolocation_dataset.csv`         | 地理位置表，包含邮编、纬度、经度、城市、州等                      |
| 9   | `product_category_name_translation.csv` | 品类名称翻译表，包含葡萄牙语品类名与英语品类名的对照                  |

## 数据规模



| 文件名                                     | 行数      | 列数  | 文件大小(MB) |
| --------------------------------------- | ------- | --- | -------- |
| `olist_orders_dataset.csv`              | 99441   | 8   | 16.84    |
| `olist_order_items_dataset.csv`         | 112650  | 7   | 14.72    |
| `olist_order_payments_dataset.csv`      | 103886  | 5   | 5.51     |
| `olist_order_reviews_dataset.csv`       | 99224   | 7   | 13.78    |
| `olist_products_dataset.csv`            | 32951   | 9   | 2.27     |
| `olist_customers_dataset.csv`           | 99441   | 5   | 8.62     |
| `olist_sellers_dataset.csv`             | 3095    | 4   | 0.17     |
| `olist_geolocation_dataset.csv`         | 1000163 | 5   | 58.44    |
| `product_category_name_translation.csv` | 71      | 2   | 0        |

### 快速统计行数

在 `Assignment` 目录下打开终端，执行以下命令可快速查看每个文件的行数（含表头）：

```cmd
for %f in (data\raw\*.csv) do @echo %~nxf & python -c "import csv; print(sum(1 for _ in open(r'data\raw\%~nxf', encoding='utf-8')))"
```

如需同时统计列数，可运行：

```python
import os, csv

raw_dir = "data/raw"
for fname in sorted(os.listdir(raw_dir)):
    if fname.endswith(".csv"):
        path = os.path.join(raw_dir, fname)
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = sum(1 for _ in reader)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"{fname}: {rows} 行, {len(header)} 列, {size_mb:.2f} MB")
```

将输出结果回填到上表中即可。

## 数据导入说明

1. 将 9 个 CSV 文件全部放入 `data/raw/` 目录；
2. 修改 `src/import_config.json` 中的数据库连接信息（host、port、user、password、database）；
3. 在 MySQL 中创建数据库：

```sql
CREATE DATABASE olist_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

4. 运行建表脚本：

```cmd
mysql -u root -p olist_ecommerce < sql/create_tables.sql
```

5. 运行数据导入脚本：

```cmd
python src/data_import.py
```

6. 导入完成后，可运行查询脚本验证数据：

```cmd
mysql -u root -p olist_ecommerce < sql/query_order_fulfillment.sql
mysql -u root -p olist_ecommerce < sql/query_delayed_orders.sql
```

## 注意事项

- 原始 CSV 文件为葡萄牙语编码，部分字段包含特殊字符，导入时需使用 `utf-8` 或 `latin1` 编码读取；
- `olist_geolocation_dataset.csv` 文件较大（约 100 万行），如仅需核心业务分析，可选择不导入该表；
- `product_category_name_translation.csv` 为辅助翻译表，行数较少（约 100 行），建议导入以支持品类名称的英文展示；
- 数据已脱敏，客户ID、卖家ID等均为哈希值，不指向真实个人或企业；
- 请勿将原始 CSV 文件提交到 Git 仓库，`.gitignore` 已配置排除规则。

## 数据字典与模型文档

详细的数据字典、表关系说明、ER 图及数据血缘信息，请参考：

- `docs/data_model/data_dictionary.md`
- `docs/data_model/table_relationships.md`
- `docs/data_model/er_diagram.md`
- `docs/data_model/relationship_schema.md`
- `docs/data_model/lineage_info.md`


