# 钢材进销存管理系统 设计文档

## 概述

简化版钢材进销存管理系统，以卡号（捆包号）作为货物唯一追踪标识，覆盖采购入库、加工管理、销售出库、库存管理和基础报表。B/S架构，本地部署，界面扁平化卡片式设计，适配电脑和平板。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Flask | 轻量级Python Web框架 |
| ORM | Flask-SQLAlchemy | 数据库操作 |
| 认证 | Flask-Login | 用户登录/权限管理 |
| 数据库 | MySQL 8 | 卡号级库存追踪和流水记录 |
| 模板 | Jinja2 | 服务端渲染 |
| 交互 | HTMX | 局部刷新，表单提交/搜索/分页 |
| 样式 | TailwindCSS (CDN) | 扁平化卡片布局，无需Node.js构建 |
| 图表 | Chart.js (CDN) | 报表趋势图 |
| 导出 | openpyxl | Excel导出 |

## 部署方式

```bash
pip install -r requirements.txt
python run.py
```

单进程运行，无需Node.js构建，无需互联网（CDN资源可本地化）。

## 用户与权限

| 角色 | 权限 |
|------|------|
| admin | 全部功能 + 用户管理 + 基础数据维护 |
| operator | 采购/加工/销售/库存/报表操作 |

## 数据模型

### 基础字典表

| 表名 | 字段 |
|------|------|
| product_name | id, name |
| brand | id, name |
| origin | id, name |
| department | id, name |
| customer | id, name, contact, phone, remark |
| supplier | id, name, contact, phone, remark |

### 用户表

| 表名 | 字段 |
|------|------|
| user | id, username, password_hash, role(admin/operator), dept_id, is_active, created_at |

### 库存表

| 表名 | 字段 |
|------|------|
| inventory | id, card_no(唯一), product_name, brand, origin, spec, qty, weight, dept_id, status(in_stock/consumed/out), created_at, updated_at |

库存按卡号逐条显示，不做汇总。

### 采购入库

| 表名 | 字段 |
|------|------|
| purchase_order | id, order_no, supplier_id, dept_id, remark(主单备注), total_qty, total_weight, operator_id, created_at |
| purchase_item | id, order_id, card_no, product_name, brand, origin, spec, qty, weight, remark |

total_qty和total_weight由明细汇总自动计算，保存时同步更新主单。

### 销售出库

| 表名 | 字段 |
|------|------|
| sales_order | id, order_no, customer_id, dept_id, remark, total_qty, total_weight, operator_id, created_at |
| sales_item | id, order_id, card_no, product_name, brand, origin, spec, qty, weight, remark |

total_qty和total_weight由明细汇总自动计算，保存时同步更新主单。

### 加工管理

| 表名 | 字段 |
|------|------|
| process_order | id, order_no, dept_id, total_qty, total_weight, operator_id, created_at |
| process_detail | id, order_id, raw_card_no, raw_spec(原卷规格), new_card_no, product_name, brand, origin, spec, qty, weight, loss_weight(手工录入) |

total_qty和total_weight由明细汇总自动计算，保存时同步更新主单。

加工为1对多：一根原料卡号可拆出多根产成品卡号。损耗手工录入。

### 流水记录

| 表名 | 字段 |
|------|------|
| transaction_log | id, card_no, type(in/out/process), product_name, spec, brand, origin, order_no, weight_before, weight_after, created_at |

## 业务流程

### 采购入库

1. 新建入库单：填写供应商、销售部门、主单备注
2. 录入明细：逐行录入卡号、品名、牌号、产地、规格、件数、吨位、备注
3. 保存：明细汇总→主单总件数/总吨位；每条明细→创建库存记录（按卡号逐条）；写入流水

### 加工管理（1对多）

1. 新建加工单：选择销售部门
2. 选择原料卡号：从库存中选择，自动带入品名、牌号、产地、规格、吨位
3. 录入产成品：可添加多行产成品
   - 新卡号：手工录入
   - 品名：下拉选择
   - 牌号：默认=原料牌号，支持下拉选择
   - 产地：默认=原料产地，支持下拉选择
   - 规格：手工录入
   - 件数、吨位：手工录入
   - 原卷规格：自动带入原料规格
   - 损耗：手工录入
4. 保存：原料卡号标记已消耗；产成品卡号创建库存记录；写入流水

### 销售出库

1. 新建出库单：填写客户、销售部门
2. 选卡号出库：从库存搜索/选择卡号，自动带入品名、规格等信息，可修改出库吨位
3. 保存：明细汇总→主单总件数/总吨位；库存标记已出库；写入流水

### 库存管理

- 卡号级库存查询：按卡号、品名、牌号、产地、部门筛选
- 按品名/牌号/产地/部门汇总视图（独立于库存明细）
- 库存状态：在库、已消耗、已出库

### 报表中心

| 报表 | 筛选条件 | 功能 |
|------|---------|------|
| 入库明细报表 | 日期/供应商/品名/部门 | 查询+导出Excel |
| 出库明细报表 | 日期/客户/品名/部门 | 查询+导出Excel |
| 库存汇总报表 | 品名/牌号/产地/部门 | 汇总+导出Excel |
| 加工损耗报表 | 日期/品名 | 加工量与损耗率+导出Excel |
| 自定义查询 | 卡号/日期范围 | 卡号全生命周期追踪+日/月趋势图 |

## UI设计

### 布局

- 左侧深色导航栏（#1e293b）+ 右侧内容区
- 导航项：工作台、采购入库、加工管理、销售出库、库存管理、报表中心、基础数据、用户管理

### 色彩

| 用途 | 色值 | 说明 |
|------|------|------|
| 侧栏 | #1e293b | 深色导航 |
| 主色 | #3b82f6 | 链接/按钮/选中态 |
| 入库 | #22c55e | 入库相关标识 |
| 加工 | #f59e0b | 加工相关标识 |
| 出库 | #ef4444 | 出库相关标识 |
| 背景 | #fefdf8 | 牛奶色主背景 |
| 卡片 | #ffffff | 白色卡片 |

### 工作台

- 4项统计卡片：当前库存件数、库存吨位、今日入库、今日出库
- 最近操作流水列表
- 快捷入口按钮

### 适配

- 响应式布局，适配电脑(≥1024px)和平板(≥768px)
- 侧栏在平板下可折叠

## 项目结构

```
wms_xz1/
├── app/
│   ├── __init__.py          # Flask应用工厂
│   ├── models.py            # SQLAlchemy模型
│   ├── auth/                # 认证模块
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/
│   ├── purchase/            # 采购入库
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── templates/
│   ├── process/             # 加工管理
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── templates/
│   ├── sales/               # 销售出库
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── templates/
│   ├── inventory/           # 库存管理
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/
│   ├── report/              # 报表中心
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/
│   ├── base_data/           # 基础数据
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/
│   ├── dashboard/           # 工作台
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/
│   ├── static/              # 静态资源
│   └── templates/           # 基础模板
│       ├── base.html        # 主布局模板
│       └── components/      # 公共组件
├── config.py                # 配置文件
├── requirements.txt         # 依赖清单
├── run.py                   # 启动入口
└── init_db.py               # 数据库初始化脚本
```
