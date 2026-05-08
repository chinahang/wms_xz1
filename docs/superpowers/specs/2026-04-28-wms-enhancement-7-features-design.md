# WMS System Enhancement Design - 7 Features

> **Date:** 2026-04-28
> **Status:** Approved

## Overview

7 enhancement features for the steel WMS system covering navigation restructuring, theoretical weight calculation, sales order UX improvements, unit price/amount fields, and edit functionality.

---

## Feature 1: Navigation Sidebar Restructure

### Current State
Sidebar has 6 flat links: 采购入库, 采购明细, 加工管理, 加工明细, 销售出库, 销售明细

### Target State
3 first-level groups, each with 2 second-level items:

| Group | Sub-items |
|-------|-----------|
| 入库台账 | 入库主单 (purchase.index) + 入库明细 (purchase.detail_list) |
| 加工台账 | 加工主单 (process.index) + 加工明细 (process.detail_list) |
| 销售台账 | 销售出库主单 (sales.index) + 销售出库明细 (sales.detail_list) |

### Implementation
- First-level items are non-clickable group headers with expand/collapse toggle
- Second-level items indented, visible when group is expanded
- Active group auto-expanded, others collapsed
- Pure CSS + minimal JS (toggle class on click)
- Rename link labels: "采购入库" → "入库主单", "加工管理" → "加工主单", "销售出库" → "销售出库主单"

### Files
- Modify: `app/templates/base.html` — restructure nav HTML + add toggle JS
- Modify: `app/static/css/custom.css` — add sub-menu styles

---

## Feature 2: Theoretical Weight Calculation (理算吨位)

### Formula
```
单张板吨位 = 厚度 * 宽度 * 长度 * 7.85 / 1,000,000,000
```

### Spec Format Convention
All spec fields use format `厚度*宽度*长度` (e.g. `1.5*1250*2500`). This is a display/business convention, not enforced at DB level.

### New Model: CalcSpec
```python
class CalcSpec(db.Model):
    __tablename__ = 'calc_spec'
    id = db.Column(db.Integer, primary_key=True)
    product_name_id = db.Column(db.Integer, db.ForeignKey('product_name.id'), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    product_name = db.relationship('ProductName', backref='calc_spec')
```

One CalcSpec per ProductName. `enabled=True` means auto-calc weight for that product name.

### Base Data: New Tab "理算维护"
- Add "理算维护" tab to `base_data/index.html`
- Table columns: 品名, 是否启用理算(toggle button)
- Toggle POST route: `/base_data/calc_spec/toggle/<id>`
- Auto-create CalcSpec rows for ProductNames that don't have one yet (lazy init on page load)

### Application in Process Module
- When user selects a product_name in process form and types a spec:
  - If that product_name has calc_spec.enabled=True
  - Parse spec: split by `*`, extract thickness/width/length as floats
  - Calculate: `weight = thickness * width * length * 7.85 / 1_000_000_000 * qty`
  - Auto-fill weight field (user can still manually override)
- Implemented as JS function triggered on `product_name` select change + spec input change

### Files
- Modify: `app/models.py` — add CalcSpec model
- Modify: `app/base_data/routes.py` — add calc_spec toggle route, pass calc_specs to index
- Modify: `app/templates/base_data/index.html` — add 理算维护 tab
- Modify: `app/process/routes.py` — pass calc_enabled_product_names to create form
- Modify: `app/templates/process/form.html` — add JS auto-calc logic
- New route: `base_data.calc_spec_toggle`

---

## Feature 3: Sales Order - Inventory Selection Modal

### Current Problem
Adding items requires searching card numbers one at a time via HTMX, very cumbersome.

### Solution
Replace single "添加明细" button with a modal dialog:

**Modal contents:**
- Filter form at top: 品名(select), 牌号(select), 产地(select), 部门(select), 卡号(text search)
- Table of available inventory (status='in_stock'): 卡号, 品名, 牌号, 产地, 规格, 件数, 吨位, 部门
- Checkbox on each row for multi-select
- Footer: "已选 N 条" + "确认添加" button

**Behavior:**
- Filter is GET request via HTMX (or full page reload), results update in modal
- "确认添加" closes modal and adds all selected rows to the sales item table
- Existing single-card search still available as fallback (or removed)

### Files
- Modify: `app/sales/routes.py` — add `available_inventory` API/route (HTMX partial)
- Modify: `app/templates/sales/form.html` — add modal HTML + JS
- Possibly new: `app/templates/sales/_available_inventory.html` — HTMX partial for inventory table

---

## Feature 4: Sales Order - Unit Price/Amount + Split Pack (拆包)

### New DB Fields
```python
# SalesItem additions:
unit_price = db.Column(db.Numeric(12, 2), default=0)
amount = db.Column(db.Numeric(14, 2), default=0)

# SalesOrder additions:
total_amount = db.Column(db.Numeric(14, 2), default=0)
```

### Sales Form Changes
- Add 单价 input column to item table
- 金额 auto-calculated: `amount = weight * unit_price` (单价为元/吨), display 2 decimal places
- Total 金额 shown in order header
- On form submit, unit_price and amount sent per item

### Split Pack (拆包) Logic
When user clicks "拆包" button on an item row:

**Expand inline section showing:**
- 可用件/张: inventory qty for that card_no
- 可用吨位: inventory weight for that card_no
- 拆包件/张: user input (integer, must be < 可用件数)
- 拆包吨位: auto-calculated = `(拆包件数 / 可用件数) * 可用吨位`, user can override
- 单价: same as parent row
- 拆包金额: 拆包吨位 * 单价

**On order submission:**
- Original inventory record: qty -= 拆包件数, weight -= 拆包吨位
- If qty reaches 0, set status='out'; otherwise status stays 'in_stock'
- The split portion is recorded as a separate SalesItem in the same order
- TransactionLog: one entry for the main item (full card), one for split portion
  - Actually: only ONE inventory card, so ONE TransactionLog with weight_before=original, weight_after=remaining

**Important:** Split pack only applies to items whose inventory has qty > 1. If qty=1, 拆包 button hidden or disabled.

### Files
- Modify: `app/models.py` — add unit_price, amount to SalesItem; total_amount to SalesOrder
- Modify: `app/sales/services.py` — handle split pack logic in create_sales_order
- Modify: `app/sales/routes.py` — parse unit_price/amount/split data from form
- Modify: `app/templates/sales/form.html` — add unit_price column, split pack UI
- Modify: `app/templates/sales/list.html` — show total_amount column

---

## Feature 5: Purchase Order - Unit Price/Amount Fields

### New DB Fields
```python
# PurchaseItem additions:
unit_price = db.Column(db.Numeric(12, 2), default=0)
amount = db.Column(db.Numeric(14, 2), default=0)

# PurchaseOrder additions:
total_amount = db.Column(db.Numeric(14, 2), default=0)
```

### Changes
- Purchase form: add 单价 input column, 金额 auto-calculated: `amount = weight * unit_price` (单价为元/吨), 2 decimal places
- Purchase list: show total_amount column
- Purchase detail list: add 单价, 金额 columns in table + Excel export
- Import Excel template: add 单价 column after 吨位
- Import preview/confirm: parse unit_price, calculate amount

### Files
- Modify: `app/models.py` — add unit_price, amount to PurchaseItem; total_amount to PurchaseOrder
- Modify: `app/purchase/routes.py` — parse unit_price/amount in create, detail_list export
- Modify: `app/purchase/services.py` — calculate total_amount, store unit_price/amount
- Modify: `app/templates/purchase/form.html` — add 单价/金额 columns
- Modify: `app/templates/purchase/list.html` — show total_amount
- Modify: `app/templates/purchase/detail_list.html` — add 单价/金额 columns
- Modify: `app/templates/purchase/import_preview.html` — add 单价 field

---

## Feature 6: Edit Buttons for Purchase/Process/Sales Orders

### Scope
Full edit: modify main order info + add/remove/modify detail rows (equivalent to recreating except order_no stays).

### Edit Logic
- Edit route: `/<module>/edit/<id>` (GET shows form pre-filled, POST saves changes)
- On POST: update order fields + rebuild items/details, then sync inventory
- **Inventory sync rules:**
  - Purchase: delete old Inventory records (by old card_nos), create new Inventory for each new item
  - Process: restore raw material Inventory to in_stock if card_no changed, set new raw to consumed; delete old new-Inventory, create new ones
  - Sales: restore old items' Inventory to in_stock, set new items' Inventory to out
- **TransactionLog:** NOT modified on edit (keep original log for audit trail)

### Reuse Form Template
- Create and edit share the same form template
- Edit mode: pass `order` and `edit_mode=True` to template
- Template pre-fills all fields from order data
- POST action changes based on mode

### Files
- Modify: `app/purchase/routes.py` — add edit route
- Modify: `app/process/routes.py` — add edit route
- Modify: `app/sales/routes.py` — add edit route
- Modify: `app/templates/purchase/form.html` — support edit mode
- Modify: `app/templates/process/form.html` — support edit mode
- Modify: `app/templates/sales/form.html` — support edit mode
- Modify: `app/templates/purchase/list.html` — add edit button
- Modify: `app/templates/process/list.html` — add edit button
- Modify: `app/templates/sales/list.html` — add edit button

---

## Feature 7: Database Migration Verification

After all features implemented, run ALTER TABLE statements for:
1. `calc_spec` table creation
2. `purchase_item`: add `unit_price DECIMAL(12,2) DEFAULT 0`, `amount DECIMAL(14,2) DEFAULT 0`
3. `purchase_order`: add `total_amount DECIMAL(14,2) DEFAULT 0`
4. `sales_item`: add `unit_price DECIMAL(12,2) DEFAULT 0`, `amount DECIMAL(14,2) DEFAULT 0`
5. `sales_order`: add `total_amount DECIMAL(14,2) DEFAULT 0`

Write a Python migration script that:
- Creates calc_spec table
- Adds all new columns (with IF NOT EXISTS check or try/except)
- Prints success/failure for each step
- Can be run idempotently

---

## Implementation Order

Recommended order (dependencies considered):

1. **DB migration** (Feature 7) — do this first so columns exist
2. **Navigation restructure** (Feature 1) — standalone, quick
3. **理算吨位** (Feature 2) — new model + base data tab + process form JS
4. **Purchase unit price/amount** (Feature 5) — simpler than sales, establish pattern
5. **Sales inventory modal** (Feature 3) — UX improvement before split pack
6. **Sales unit price/amount + split pack** (Feature 4) — depends on modal
7. **Edit buttons** (Feature 6) — most complex, do last when all fields are stable
