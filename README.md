# 钢材进销存管理系统

基于 Flask + MySQL 8 的钢材进销存管理系统，以卡号（捆包号）作为货物唯一追踪标识。

---

## 环境要求（Windows 10）

- **Python** 3.10 或以上：https://www.python.org/downloads/ （安装时勾选 "Add Python to PATH"）
- **MySQL** 8.0：https://dev.mysql.com/downloads/installer/
- **Git**（可选）：https://git-scm.com/download/win

---

## 安装步骤

### 1. 安装 MySQL 8.0

安装后打开 MySQL 命令行或 Navicat，创建数据库：

```sql
CREATE DATABASE steel_wms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 安装 Python 3.10+

从 python.org 下载安装。验证安装：

```cmd
python --version
```

### 3. 创建虚拟环境（推荐）

在项目根目录打开 CMD 或 PowerShell：

```cmd
python -m venv venv
```

激活虚拟环境：

```cmd
venv\Scripts\activate
```

### 4. 安装依赖

```cmd
pip install -r requirements.txt
```

### 5. 配置环境变量

复制 `.env.example` 为 `.env`：

```cmd
copy .env.example .env
```

编辑 `.env` 文件，修改数据库连接：

```env
SECRET_KEY=改成你自己的随机字符串
DATABASE_URI=mysql+pymysql://root:你的密码@localhost:3306/steel_wms?charset=utf8mb4
FLASK_CONFIG=development
FLASK_DEBUG=1
```

### 6. 初始化数据库

```cmd
python init_db.py
```

### 7. 启动系统

```cmd
python run.py
```

浏览器访问 **http://localhost:5000**

---

## 局域网访问

服务器启动后默认监听 `0.0.0.0:5000`（所有网卡），局域网其他电脑可通过服务器 IP 访问：

```
http://192.168.x.x:5000
```

如果无法访问，检查 Windows 防火墙：
1. 打开「Windows 防火墙」→「高级设置」
2. 入站规则 → 新建规则 → 端口 → TCP 5000 → 允许连接

---

## 后台运行（可选）

如需在后台持续运行不显示窗口，可用以下方式之一：

**方法一：无窗口运行**

```cmd
pythonw run.py
```

**方法二：自启动脚本**

创建 `start.bat`：

```cmd
@echo off
cd /d "C:\你的项目路径"
call venv\Scripts\activate
python run.py
```

将此文件放入 Windows 启动文件夹（`shell:startup`）即可开机自启。

---

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |

---

## 功能模块

| 模块 | 说明 |
|------|------|
| 工作台 | 库存统计、今日出入库、最近操作流水、快捷入口 |
| 采购入库 | 新建入库单、录入卡号明细、自动创建库存和流水 |
| 加工管理 | 选原料卡号、录入产成品（1 对多） |
| 销售出库 | 选卡号出库、自动同步库存状态和流水、支持提货单/销售单打印 |
| 库存管理 | 卡号级库存查询、按品名/牌号/产地/部门汇总 |
| 报表中心 | 入库/出库/库存/加工损耗报表、自定义查询、导出 Excel |
| 基础数据 | 品名/牌号/产地/部门/仓库/客户/供应商管理 |
| 用户管理 | 添加用户、重置密码、启用/禁用（管理员） |

---

## 技术栈

- 后端：Flask + Flask-SQLAlchemy + Flask-Login
- 数据库：MySQL 8 (PyMySQL)
- 前端：Jinja2 + TailwindCSS + Chart.js
- 导出：openpyxl
- 打印：浏览器打印（HTML to Print，针式打印机适配）
