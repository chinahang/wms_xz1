from datetime import datetime, date
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')
    dept_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    dept = db.relationship('Department', backref='users')


class ProductName(db.Model):
    __tablename__ = 'product_name'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Brand(db.Model):
    __tablename__ = 'brand'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Origin(db.Model):
    __tablename__ = 'origin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class CalcSpec(db.Model):
    __tablename__ = 'calc_spec'
    id = db.Column(db.Integer, primary_key=True)
    product_name_id = db.Column(db.Integer, db.ForeignKey('product_name.id'), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    product_name = db.relationship('ProductName', backref='calc_spec')


class Warehouse(db.Model):
    __tablename__ = 'warehouse'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Unit(db.Model):
    __tablename__ = 'unit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    remark = db.Column(db.Text)


class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    card_no = db.Column(db.String(100), unique=True, nullable=False, index=True)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    dept_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    status = db.Column(db.String(20), nullable=False, default='in_stock')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    dept = db.relationship('Department', backref='inventories')
    warehouse = db.relationship('Warehouse', backref='inventories')


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    dept_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    remark = db.Column(db.Text)
    total_qty = db.Column(db.Integer, nullable=False, default=0)
    total_weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(14, 2), default=0)
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.now)
    supplier = db.relationship('Unit', foreign_keys=[supplier_id], backref='purchase_orders')
    dept = db.relationship('Department', backref='purchase_orders')
    operator = db.relationship('User', backref='purchase_orders')
    items = db.relationship('PurchaseItem', backref='order', cascade='all, delete-orphan')


class PurchaseItem(db.Model):
    __tablename__ = 'purchase_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    card_no = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    unit_price = db.Column(db.Numeric(12, 2), default=0)
    amount = db.Column(db.Numeric(14, 2), default=0)
    warehouse = db.Column(db.String(100))
    remark = db.Column(db.Text)


class SalesOrder(db.Model):
    __tablename__ = 'sales_order'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    dept_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    remark = db.Column(db.Text)
    total_qty = db.Column(db.Integer, nullable=False, default=0)
    total_weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(14, 2), default=0)
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.now)
    customer = db.relationship('Unit', foreign_keys=[customer_id], backref='sales_orders')
    dept = db.relationship('Department', backref='sales_orders')
    operator = db.relationship('User', backref='sales_orders')
    items = db.relationship('SalesItem', backref='order', cascade='all, delete-orphan')


class SalesItem(db.Model):
    __tablename__ = 'sales_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('sales_order.id'), nullable=False)
    card_no = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    split_qty = db.Column(db.Integer, default=0)
    split_weight = db.Column(db.Numeric(12, 3), default=0)
    unit_price = db.Column(db.Numeric(12, 2), default=0)
    amount = db.Column(db.Numeric(14, 2), default=0)
    warehouse = db.Column(db.String(100))
    remark = db.Column(db.Text)


class ProcessOrder(db.Model):
    __tablename__ = 'process_order'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    total_qty = db.Column(db.Integer, nullable=False, default=0)
    total_weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.now)
    dept = db.relationship('Department', backref='process_orders')
    operator = db.relationship('User', backref='process_orders')
    details = db.relationship('ProcessDetail', backref='order', cascade='all, delete-orphan')


class ProcessDetail(db.Model):
    __tablename__ = 'process_detail'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('process_order.id'), nullable=False)
    raw_card_no = db.Column(db.String(100), nullable=False)
    raw_spec = db.Column(db.String(200), nullable=False)
    new_card_no = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    loss_weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)


class TransactionLog(db.Model):
    __tablename__ = 'transaction_log'
    id = db.Column(db.Integer, primary_key=True)
    card_no = db.Column(db.String(100), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    order_no = db.Column(db.String(50), nullable=False)
    weight_before = db.Column(db.Numeric(12, 3), default=0)
    weight_after = db.Column(db.Numeric(12, 3), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
