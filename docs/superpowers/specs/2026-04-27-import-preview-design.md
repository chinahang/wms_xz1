# Excel导入校验页设计

## 背景

当前Excel导入直接写入数据库，数据错误（供应商不存在、品名不匹配等）导致IntegrityError。需要一个校验预览页面，让用户在上传后检查、修正数据，确认无误后再入库。

## 流程

```
上传Excel → /purchase/import (解析+校验+存session) → /purchase/import/preview (校验页面)
    → 用户编辑/删行 → /purchase/import/confirm (重新校验+写入)
```

## 约束

- 最多500行数据，超出拒绝上传
- 校验页顶部显示 `当前 N / 500 行`
- 供应商/部门/品名/牌号/产地名称必须匹配基础数据，不匹配时标红，不自动新建
- 有标红字段时，确认导入按钮可点，后端重新校验；仍有错误则拒绝入库并回到预览页

## 路由

### POST /purchase/import
- 解析Excel文件
- 读取基础数据（供应商、部门、品名、牌号、产地）用于校验
- 行数 > 500 → flash错误，重定向回列表
- 每行校验：
  - 供应商名称不在Supplier表 → supplier字段标红
  - 销售部门名称不在Department表 → dept字段标红
  - 品名不在ProductName表 → product_name字段标红
  - 牌号不在Brand表 → brand字段标红
  - 产地不在Origin表 → origin字段标红
  - 卡号为空 → card_no字段标红
  - 吨位 ≤ 0 → weight字段标红
- 结果存入 `session['import_preview_data']`
- 重定向到 `/purchase/import/preview`

### GET /purchase/import/preview
- 从session读取 `import_preview_data`
- 无数据 → 重定向回列表
- 渲染可编辑表格

### POST /purchase/import/confirm
- 接收表单数据（动态行数，每行所有字段）
- 重新校验全部字段
- 仍有标红字段 → flash错误，回到预览页
- 全部通过 → 按供应商+部门分组，每组生成一个入库单
- 清除session，flash成功，重定向到列表

## 校验页面 (import_preview.html)

### 布局
- 顶部：标题"导入数据校验"，统计信息（总行数 N / 500，错误行数 M）
- 中间：可编辑表格
- 底部：确认导入按钮 + 取消按钮

### 表格
- 列：序号 | 供应商 | 销售部门 | 品名 | 卡号 | 牌号 | 产地 | 规格 | 件数 | 吨位 | 备注 | 操作
- 所有字段为 input 可编辑
- 标红字段：input 边框变为红色背景 `bg-red-50 border-red-400`
- 操作列：删除按钮，删除该行
- 表单提交时包含所有可见行数据

### JS交互
- 删除行：移除tr，更新序号
- 确认按钮：始终可点击（前端无法实时校验名称是否匹配基础数据，由后端做最终校验）

## 数据结构

session key: `import_preview_data`

每行结构:
```json
{
  "supplier": "供应商A",
  "dept": "销售一部",
  "product_name": "螺纹钢",
  "card_no": "KH001",
  "brand": "HRB400",
  "origin": "首钢",
  "spec": "Φ12",
  "qty": 10,
  "weight": 25.5,
  "remark": "",
  "errors": {
    "supplier": true,
    "dept": false,
    "product_name": false,
    "card_no": false,
    "brand": false,
    "origin": false,
    "weight": false
  }
}
```

## 入库逻辑

确认导入时，按 (supplier, dept) 分组，每组生成一个 PurchaseOrder：
- supplier_name → 查 Supplier 表获取 id
- dept_name → 查 Department 表获取 id
- 每行生成一个 PurchaseItem + Inventory + TransactionLog

## 修改文件清单

- `app/purchase/routes.py` — 修改 import_excel，新增 import_preview 和 import_confirm
- `app/templates/purchase/import_preview.html` — 新建校验页面模板
- `app/templates/purchase/list.html` — Excel导入按钮的 form action 不变
