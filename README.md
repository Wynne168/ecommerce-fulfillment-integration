# INT6164 电商履约整合项目

## 项目名称

面向多商家电商平台的订单履约数据整合与质量治理系统设计

## 项目概述

本项目面向电商平台客服、商家运营人员和平台管理者，整合订单、商品、卖家、支付及配送相关信息，支持履约查询、延迟识别、质量检查和来源追踪。原型重点实现订单查询、延迟订单查询、质量结果与来源展示。

## 数据集来源

- **数据集名称**：Brazilian E-Commerce Public Dataset by Olist
- **发布平台**：Kaggle
- **下载地址**：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **数据提供方**：Olist S.A.（巴西知名电商平台）
- **授权许可**：Kaggle 数据集许可（详见页面）
- **时间范围**：2016年9月 至 2018年8月
- **数据规模**：约10万条订单记录，涵盖10个CSV数据文件

详细的数据来源说明、文件清单、字段说明及获取步骤请参考 [data/README.md](data/README.md)。

## 目录结构

```
├── README.md                  # 项目说明（本文件）
├── data/README.md             # 数据来源、获取及放置说明（组员A）
├── data/
│   ├── raw/                   # 原始CSV数据（需自行下载，不纳入仓库）
│   ├── cleaned/               # 清洗后数据
│   └── test/                  # 测试用小型数据
├── docs/
│   ├── requirements/          # 需求与业务规则（组长）
│   ├── data_model/            # 数据字典、ER图、关系模式（组员A）
│   ├── architecture/          # 架构、流程、选型与权衡（组员B）
│   ├── governance/            # 质量、元数据、血缘、安全（组员C）
│   └── report_sections/       # 各成员报告正文（各成员）
├── sql/                       # 建表、视图、查询及索引脚本（组员A、B）
│   ├── create_tables.sql      # 建表脚本 + 索引 + 视图
│   ├── import_data.sql        # 数据导入脚本
│   ├── query_order_fulfillment.sql   # 查询1：订单履约详情
│   ├── query_delayed_orders.sql       # 查询2：延迟订单筛选
│   └── verify_query_correctness.sql   # 查询验证脚本
├── src/                       # 导入、处理、检查及运行记录代码（组员A、B、C）
│   ├── data_import.py         # Python数据导入脚本
│   └── import_config.json     # 数据库连接配置
├── app/                       # 原型界面（组员B）
├── tests/                     # 查询、质量及接口测试（组员A、B、C）
│   ├── test_queries.py        # 查询测试
│   └── test_config.json       # 测试数据库配置
├── evidence/                  # 核对结果、测试记录、性能证据（各负责人）
│   ├── verification_record.md      # 样例核对记录
│   └── query_verification_evidence.md  # 查询验证证据
└── presentation/              # 统一PPT、讲稿、演示说明（组员D）
```

## 成员分工

| 成员 | 职责 | 负责内容 |
|------|------|---------|
| **组长** | 业务需求、规则确认、端到端验收、综合评估及报告整合 | 需求定义、业务口径、进度跟进、验收、综合评估、报告整合 |
| **组员A** | 数据核验、数据库模型、数据导入和业务查询 | 数据来源核验、数据字典、ER图、建表脚本、业务查询SQL、查询验证、数据血缘信息 |
| **组员B** | 架构与选型、运行环境、原型界面及处理运行记录 | 架构设计、技术选型、原型搭建、运行日志、性能验证、设计权衡 |
| **组员C** | 数据质量、元数据、血缘、可观测性规则及安全隐私 | 质量规则、异常检查、元数据目录、指标血缘、可观测性规则、安全隐私方案 |
| **组员D** | 统一制作PPT、演示材料、操作说明和排练组织 | PPT制作、演示流程设计、操作说明、备用材料、排练组织 |

## 快速开始

### 1. 准备数据集

从 Kaggle 下载 [Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)，将下载的 CSV 文件放入 `data/raw/` 目录。

### 2. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE ecommerce_fulfillment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行建表脚本
mysql -u username -p ecommerce_fulfillment < sql/create_tables.sql
```

### 3. 导入数据

**方式A（推荐，速度快）：**

```bash
# 修改 sql/import_data.sql 中的文件路径为实际路径
mysql -u username -p ecommerce_fulfillment < sql/import_data.sql
```

**方式B（Python脚本）：**

```bash
# 修改 src/import_config.json 中的数据库连接信息
pip install pandas sqlalchemy pymysql
python src/data_import.py
```

### 4. 运行查询

```bash
# 查询1：按订单号查询履约详情
mysql -u username -p ecommerce_fulfillment < sql/query_order_fulfillment.sql

# 查询2：延迟订单筛选
mysql -u username -p ecommerce_fulfillment < sql/query_delayed_orders.sql

# 查询验证
mysql -u username -p ecommerce_fulfillment < sql/verify_query_correctness.sql
```

### 5. 运行测试

```bash
# 修改 tests/test_config.json 中的数据库连接信息
pip install pytest
python -m pytest tests/test_queries.py -v
```

## 项目计划

- **项目周期**：2026年11月4日 至 11月18日
- **材料整合完成日期**：11月14日
- **路演日期**：11月18日

## 贡献说明

本项目以每人20%为基础，考虑组长额外承担进度协调、跨模块验收、综合评估和最终报告整合，暂定组长计划贡献比例为22%，其余四位组员各为19.5%，合计100%。

最终贡献比例将根据实际完成情况，由全组讨论确认。

## 注意事项

1. 原始大文件、本地数据库、密码、密钥和本地配置不纳入仓库，已使用 `.gitignore` 排除。
2. 小型测试数据可按授权与用途标注后保存。
3. 各成员分别维护自己的报告章节文件，最终Word由组长整合，PPT由D统一维护。
4. 每次提交需说明具体变化，避免只写"更新"。
