from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user
from werkzeug.security import generate_password_hash

from app import db
from app.base_data import base_data_bp
from app.models import (ProductName, Brand, Origin, Department, Unit, User, CalcSpec, Warehouse,
                         Inventory, PurchaseItem, ProcessDetail, SalesItem, PurchaseOrder, ProcessOrder, SalesOrder)
from app.utils import admin_required


@base_data_bp.route('/')
def index():
    active_tab = request.args.get('tab', 'product_name')
    product_names = ProductName.query.order_by(ProductName.id).all()
    brands = Brand.query.order_by(Brand.id).all()
    origins = Origin.query.order_by(Origin.id).all()
    departments = Department.query.order_by(Department.id).all()
    units = Unit.query.order_by(Unit.id).all()
    calc_specs = CalcSpec.query.order_by(CalcSpec.id).all()
    warehouses = Warehouse.query.order_by(Warehouse.id).all()
    return render_template('base_data/index.html',
                           active_tab=active_tab,
                           product_names=product_names,
                           brands=brands,
                           origins=origins,
                           departments=departments,
                           units=units,
                           calc_specs=calc_specs,
                           warehouses=warehouses)


def _tab_redirect(tab):
    return redirect(url_for('base_data.index', tab=tab) + '#tab-' + tab)


@base_data_bp.route('/product_name/add', methods=['POST'])
def product_name_add():
    name = request.form.get('name', '').strip()
    if name:
        existing = ProductName.query.filter_by(name=name).first()
        if existing:
            flash('该品名已存在', 'error')
        else:
            db.session.add(ProductName(name=name))
            db.session.commit()
            flash('品名添加成功', 'success')
    return _tab_redirect('product_name')


@base_data_bp.route('/product_name/delete/<int:id>', methods=['POST'])
def product_name_delete(id):
    item = ProductName.query.get_or_404(id)
    if Inventory.query.filter_by(product_name=item.name).first() or \
       PurchaseItem.query.filter_by(product_name=item.name).first() or \
       ProcessDetail.query.filter_by(product_name=item.name).first() or \
       SalesItem.query.filter_by(product_name=item.name).first() or \
       CalcSpec.query.filter_by(product_name_id=item.id).first():
        flash('该品名有业务数据关联，无法删除', 'error')
        return _tab_redirect('product_name')
    db.session.delete(item)
    db.session.commit()
    flash('品名已删除', 'success')
    return _tab_redirect('product_name')


@base_data_bp.route('/brand/add', methods=['POST'])
def brand_add():
    name = request.form.get('name', '').strip()
    if name:
        existing = Brand.query.filter_by(name=name).first()
        if existing:
            flash('该牌号已存在', 'error')
        else:
            db.session.add(Brand(name=name))
            db.session.commit()
            flash('牌号添加成功', 'success')
    return _tab_redirect('brand')


@base_data_bp.route('/brand/delete/<int:id>', methods=['POST'])
def brand_delete(id):
    item = Brand.query.get_or_404(id)
    if Inventory.query.filter_by(brand=item.name).first() or \
       PurchaseItem.query.filter_by(brand=item.name).first() or \
       ProcessDetail.query.filter_by(brand=item.name).first() or \
       SalesItem.query.filter_by(brand=item.name).first():
        flash('该牌号有业务数据关联，无法删除', 'error')
        return _tab_redirect('brand')
    db.session.delete(item)
    db.session.commit()
    flash('牌号已删除', 'success')
    return _tab_redirect('brand')


@base_data_bp.route('/origin/add', methods=['POST'])
def origin_add():
    name = request.form.get('name', '').strip()
    if name:
        existing = Origin.query.filter_by(name=name).first()
        if existing:
            flash('该产地已存在', 'error')
        else:
            db.session.add(Origin(name=name))
            db.session.commit()
            flash('产地添加成功', 'success')
    return _tab_redirect('origin')


@base_data_bp.route('/origin/delete/<int:id>', methods=['POST'])
def origin_delete(id):
    item = Origin.query.get_or_404(id)
    if Inventory.query.filter_by(origin=item.name).first() or \
       PurchaseItem.query.filter_by(origin=item.name).first() or \
       ProcessDetail.query.filter_by(origin=item.name).first() or \
       SalesItem.query.filter_by(origin=item.name).first():
        flash('该产地有业务数据关联，无法删除', 'error')
        return _tab_redirect('origin')
    db.session.delete(item)
    db.session.commit()
    flash('产地已删除', 'success')
    return _tab_redirect('origin')


@base_data_bp.route('/department/add', methods=['POST'])
def department_add():
    name = request.form.get('name', '').strip()
    if name:
        existing = Department.query.filter_by(name=name).first()
        if existing:
            flash('该部门已存在', 'error')
        else:
            db.session.add(Department(name=name))
            db.session.commit()
            flash('部门添加成功', 'success')
    return _tab_redirect('department')


@base_data_bp.route('/department/delete/<int:id>', methods=['POST'])
def department_delete(id):
    item = Department.query.get_or_404(id)
    if Inventory.query.filter_by(dept_id=item.id).first() or \
       PurchaseOrder.query.filter_by(dept_id=item.id).first() or \
       ProcessOrder.query.filter_by(dept_id=item.id).first() or \
       SalesOrder.query.filter_by(dept_id=item.id).first() or \
       User.query.filter_by(dept_id=item.id).first():
        flash('该部门有业务数据关联，无法删除', 'error')
        return _tab_redirect('department')
    db.session.delete(item)
    db.session.commit()
    flash('部门已删除', 'success')
    return _tab_redirect('department')


@base_data_bp.route('/unit/add', methods=['POST'])
def unit_add():
    name = request.form.get('name', '').strip()
    contact = request.form.get('contact', '').strip()
    phone = request.form.get('phone', '').strip()
    remark = request.form.get('remark', '').strip()
    if name:
        db.session.add(Unit(name=name, contact=contact, phone=phone, remark=remark))
        db.session.commit()
        flash('单位添加成功', 'success')
    return _tab_redirect('unit')


@base_data_bp.route('/unit/delete/<int:id>', methods=['POST'])
def unit_delete(id):
    item = Unit.query.get_or_404(id)
    if SalesOrder.query.filter_by(customer_id=item.id).first() or \
       PurchaseOrder.query.filter_by(supplier_id=item.id).first():
        flash('该单位有出库单或入库单关联，无法删除', 'error')
        return _tab_redirect('unit')
    db.session.delete(item)
    db.session.commit()
    flash('单位已删除', 'success')
    return _tab_redirect('unit')


@base_data_bp.route('/calc_spec/add', methods=['POST'])
def calc_spec_add():
    product_name_id = request.form.get('product_name_id', type=int)
    enabled = request.form.get('enabled') == 'on'
    if product_name_id:
        existing = CalcSpec.query.filter_by(product_name_id=product_name_id).first()
        if existing:
            flash('该品名已设置理算', 'error')
        else:
            db.session.add(CalcSpec(product_name_id=product_name_id, enabled=enabled))
            db.session.commit()
            flash('理算设置添加成功', 'success')
    return _tab_redirect('calc_spec')


@base_data_bp.route('/calc_spec/toggle/<int:id>', methods=['POST'])
def calc_spec_toggle(id):
    item = CalcSpec.query.get_or_404(id)
    item.enabled = not item.enabled
    db.session.commit()
    flash('理算状态已更新', 'success')
    return _tab_redirect('calc_spec')


@base_data_bp.route('/calc_spec/delete/<int:id>', methods=['POST'])
def calc_spec_delete(id):
    item = CalcSpec.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('理算设置已删除', 'success')
    return _tab_redirect('calc_spec')


@base_data_bp.route('/warehouse/add', methods=['POST'])
def warehouse_add():
    name = request.form.get('name', '').strip()
    if name:
        existing = Warehouse.query.filter_by(name=name).first()
        if existing:
            flash('该仓库已存在', 'error')
        else:
            db.session.add(Warehouse(name=name))
            db.session.commit()
            flash('仓库添加成功', 'success')
    return _tab_redirect('warehouse')


@base_data_bp.route('/warehouse/delete/<int:id>', methods=['POST'])
def warehouse_delete(id):
    item = Warehouse.query.get_or_404(id)
    if Inventory.query.filter_by(warehouse_id=item.id).first():
        flash('该仓库有库存关联，无法删除', 'error')
        return _tab_redirect('warehouse')
    db.session.delete(item)
    db.session.commit()
    flash('仓库已删除', 'success')
    return _tab_redirect('warehouse')


@base_data_bp.route('/users')
@admin_required
def user_list():
    users = User.query.all()
    departments = Department.query.all()
    return render_template('user/list.html', users=users, departments=departments)


@base_data_bp.route('/user/add', methods=['POST'])
@admin_required
def user_add():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'operator')
    dept_id = request.form.get('dept_id', type=int)
    if username and password:
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('用户名已存在', 'error')
        else:
            user = User(username=username,
                        password_hash=generate_password_hash(password),
                        role=role,
                        dept_id=dept_id)
            db.session.add(user)
            db.session.commit()
            flash('用户添加成功', 'success')
    else:
        flash('用户名和密码不能为空', 'error')
    return redirect(url_for('base_data.user_list'))


@base_data_bp.route('/user/reset_password', methods=['POST'])
@admin_required
def user_reset_password():
    user_id = request.form.get('user_id', type=int)
    new_password = request.form.get('new_password', '').strip()
    if user_id and new_password:
        user = User.query.get_or_404(user_id)
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('密码重置成功', 'success')
    else:
        flash('请输入新密码', 'error')
    return redirect(url_for('base_data.user_list'))


@base_data_bp.route('/user/toggle_active', methods=['POST'])
@admin_required
def user_toggle_active():
    user_id = request.form.get('user_id', type=int)
    if user_id:
        user = User.query.get_or_404(user_id)
        user.is_active = not user.is_active
        db.session.commit()
        flash('用户状态已更新', 'success')
    return redirect(url_for('base_data.user_list'))
