# 供应商/客户合并为"单位名称维护" — 设计文档

## 概述

将 Supplier（供应商）和 Customer（客户）两张表合并为一张 Unit（单位名称）表。两个业务模块（采购/销售）分别通过 `type` 字段区分。

---

## 一、数据库变更

### 1.1 新表

```sql
CREATE TABLE unit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'supplier',
    contact VARCHAR(50),
    phone VARCHAR(20),
    remark TEXT
);
```

`type` 取值：`supplier`（供应商）、`customer`（客户）。

### 1.2 外键变更

| 表 | 列 | 原 FK | 新 FK |
|----|-----|-------|-------|
| purchase_order | supplier_id | supplier.id | unit.id |
| sales_order | customer_id | customer.id | unit.id |

**列名不变**（supplier_id / customer_id 保持不变）。

### 1.3 数据迁移步骤

1. 创建 unit 表
2. 复制 supplier 数据（type='supplier'），记录 old_id → new_id
3. 复制 customer 数据（type='customer'），记录 old_id → new_id
4. 更新 purchase_order.supplier_id 使用旧→新 ID 映射
5. 更新 sales_order.customer_id 使用旧→新 ID 映射
6. 删除 purchase_order 旧外键约束
7. 删除 sales_order 旧外键约束
8. 添加新外键（purchase_order.supplier_id → unit.id, sales_order.customer_id → unit.id）
9. 删除 supplier 表
10. 删除 customer 表

---

## 二、模型变更（models.py）

删除 `Supplier` 和 `Customer` 类，新增 `Unit` 类。

### 2.1 Unit 类

```python
class Unit(db.Model):
    __tablename__ = 'unit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='supplier')
    contact = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    remark = db.Column(db.Text)
```

### 2.2 PurchaseOrder FK 关系变更

```python
class PurchaseOrder(db.Model):
    supplier_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    supplier = db.relationship('Unit', foreign_keys=[supplier_id],
                               backref='purchase_orders')
```

### 2.3 SalesOrder FK 关系变更

```python
class SalesOrder(db.Model):
    customer_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    customer = db.relationship('Unit', foreign_keys=[customer_id],
                               backref='sales_orders')
```

### 2.4 关键说明

- `order.supplier.name` 和 `order.customer.name` 模板写法完全不变
- 两个 relationship 使用不同的 `backref` 名（`purchase_orders` / `sales_orders`），避免冲突
- `foreign_keys=` 参数明确指定 FK 列，避免 SQLAlchemy 歧义

---

## 三、路由变更

### 3.1 base_data/routes.py

| 当前 | 改后 |
|------|------|
| Tab 分两个（供应商/客户） | 合并为一个 Tab（单位名称） |
| `customer_add/customer_delete` 路由 | 改为 `unit_add/unit_delete` 路由 |
| `supplier_add/supplier_delete` 路由 | 删除 |
| query `Customer.query.all()` / `Supplier.query.all()` | `Unit.query.order_by(Unit.id).all()` |
| 模板变量 `customers=`, `suppliers=` | 合并为 `units=` |

**新增表单字段**：`type`（供应商/客户 单选），添加单位时可同时选择类型。

### 3.2 purchase/routes.py

| 当前 | 改后 |
|------|------|
| `Supplier.query.all()` | `Unit.query.filter_by(type='supplier').all()` |
| 模板变量名 `suppliers=` | 保持不变（名称为别名，不影响功能） |
| import 中的 `Supplier` | 改为 `Unit` |
| 删除检查 `Supplier.query` | 改为 `Unit.query` |

### 3.3 sales/routes.py

| 当前 | 改后 |
|------|------|
| `Customer.query.all()` | `Unit.query.filter_by(type='customer').all()` |
| 模板变量名 `customers=` | 保持不变 |
| import 中的 `Customer` | 改为 `Unit` |
| 删除检查 `Customer.query` | 改为 `Unit.query` |

### 3.4 report/routes.py

| 当前 | 改后 |
|------|------|
| `Supplier.query.all()` | `Unit.query.filter_by(type='supplier').all()` |
| `Customer.query.all()` | `Unit.query.filter_by(type='customer').all()` |

---

## 四、模板变更

### 4.1 base_data/index.html

- 删除"客户"tab 和"供应商"tab
- 新增一个"单位名称"tab
- 表格列：名称、类型（供应商/客户标签）、联系人、电话、备注、操作
- 新增表单增加 `type` 字段（单选框：供应商 / 客户）
- 删除表单 action 改为 `url_for('base_data.unit_delete', id=item.id)`

### 4.2 purchase/form.html — create/edit 模式

- 供应商下拉 `<select name="supplier_id">` 的变量名 `suppliers` 不变
- `{% for s in suppliers %}` 不变（路由层已改为 type='supplier' filter）

### 4.3 purchase/list.html

- 供应商筛选下拉改为 `{% for u in suppliers %}`（变量名不变）
- `order.supplier.name` 不变

### 4.4 purchase/detail_list.html

- 同上

### 4.5 purchase/import_preview.html

- datalist `supplier_names` 不变（路由层传递）

### 4.6 sales/form.html — create/edit 模式

- 客户下拉变量名 `customers` 不变
- `order.customer.name` 不变

### 4.7 sales/list.html

- 客户筛选下拉变量名 `customers` 不变
- `order.customer.name` 不变

### 4.8 sales/detail_list.html

- 同上

### 4.9 sales/print_delivery.html / print_invoice.html

- `order.customer.name` 不变

### 4.10 report/purchase.html / report/sales.html

- 下拉变量名不变；`order.supplier.name` / `order.customer.name` 不变

---

## 五、迁移脚本（migrate_merge_unit.py）

独立脚本，通过 PyMySQL 直接操作数据库。

**执行流程**：

```
1. 连接数据库（同 import_base_data.py 的方式读取 .env）
2. 创建 unit 表
3. 复制 supplier → unit (type='supplier')，构建 old_id:new_id 字典
4. 复制 customer → unit (type='customer')，构建 old_id:new_id 字典
5. ALTER TABLE purchase_order DROP FOREIGN KEY（如有）
6. ALTER TABLE sales_order DROP FOREIGN KEY（如有）
7. 更新 purchase_order 的 supplier_id（遍历映射字典逐条 UPDATE）
8. 更新 sales_order 的 customer_id（遍历映射字典逐条 UPDATE）
9. ALTER TABLE purchase_order ADD FOREIGN KEY (supplier_id) REFERENCES unit(id)
10. ALTER TABLE sales_order ADD FOREIGN KEY (customer_id) REFERENCES unit(id)
11. DROP TABLE supplier
12. DROP TABLE customer
13. 打印迁移统计
```

**安全特性**：
- 每步执行前打印日志
- 失败回滚（使用事务包装）
- 迁移前检查表是否存在

---

## 六、测试检查点

### 6.1 基础数据

- [ ] 单位名称 Tab 正常显示，列出所有合并后的数据
- [ ] 新增单位时能选择类型（供应商/客户）
- [ ] 编辑单位（支持修改名称、类型、联系方式）
- [ ] 删除单位（有业务关联的数据无法删除）

### 6.2 采购管理

- [ ] 新建入库单，供应商下拉只显示 type='supplier' 的单位
- [ ] 可正常选择供应商并创建入库单
- [ ] 入库单列表，供应商列正常显示名称
- [ ] 入库明细列表，供应商筛选正常
- [ ] Excel 导入预览，供应商 datalist 正常

### 6.3 销售管理

- [ ] 新建出库单，客户下拉只显示 type='customer' 的单位
- [ ] 可正常选择客户并创建出库单
- [ ] 出库单列表，客户列正常显示名称
- [ ] 出库明细列表，客户筛选正常
- [ ] 打印提货单/销售单，购货单位正常显示

### 6.4 报表

- [ ] 采购报表供应商筛选正常
- [ ] 销售报客户筛选正常

---

## 七、文件变更汇总

| 文件 | 操作 | 难度 |
|------|------|------|
| `migrate_merge_unit.py` | **新增** | 中 |
| `models.py` | 修改 | 中 |
| `base_data/routes.py` | 修改 | 中 |
| `base_data/index.html` | 修改 | 中 |
| `purchase/routes.py` | 修改 | 低（仅 import + query） |
| `sales/routes.py` | 修改 | 低（仅 import + query） |
| `report/routes.py` | 修改 | 低（仅 import + query） |
| `import_base_data.py` | 修改 | 低（Sheet 名合并） |
| 模板（purchase/sales） | **基本不变** | - |

模板文件因 `order.supplier.name` / `order.customer.name` 写法不变，几乎无需改动。

---

## 八、回滚方案

迁移脚本执行前备份数据库。如需回滚，执行 SQL：

```sql
CREATE TABLE supplier AS SELECT id, name, contact, phone, remark FROM unit WHERE type='supplier';
CREATE TABLE customer AS SELECT id, name, contact, phone, remark FROM unit WHERE type='customer';
-- 恢复外键
DROP TABLE unit;
```

或直接通过数据库备份恢复。
