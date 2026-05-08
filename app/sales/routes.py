from flask import render_template, request, redirect, url_for, flash, current_app, send_file, abort
from flask_login import login_required, current_user
from app.sales import sales_bp
from app.sales.services import create_sales_order
from app.models import SalesOrder, SalesItem, Unit, Department, Inventory, TransactionLog, ProductName, Brand, Origin, Warehouse
from app import db
from datetime import date as date_type, timedelta
import openpyxl
from io import BytesIO
import re
from datetime import datetime


@sales_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    order_no = request.args.get('order_no', '').strip()
    customer_name = request.args.get('customer_name', '').strip()
    spec = request.args.get('spec', '').strip()
    remark_contains = request.args.get('remark', '').strip()
    dept_id = request.args.get('dept_id', 0, type=int)

    query = SalesOrder.query
    if date_start:
        query = query.filter(SalesOrder.order_date >= date_start)
    if date_end:
        query = query.filter(SalesOrder.order_date <= date_end)
    if order_no:
        query = query.filter(SalesOrder.order_no.contains(order_no))
    if customer_name:
        query = query.join(Unit, SalesOrder.customer_id == Unit.id).filter(Unit.name.contains(customer_name))
    if spec:
        sub = db.session.query(SalesItem.order_id).filter(SalesItem.spec.contains(spec))
        query = query.filter(SalesOrder.id.in_(sub))
    if remark_contains:
        query = query.filter(SalesOrder.remark.contains(remark_contains))
    if dept_id:
        query = query.filter(SalesOrder.dept_id == dept_id)

    pagination = query.order_by(SalesOrder.order_date.desc(), SalesOrder.created_at.desc()).paginate(
        page=page, per_page=current_app.config['PER_PAGE'], error_out=False
    )
    units = Unit.query.all()
    departments = Department.query.all()
    total_qty_sum = sum(o.total_qty for o in pagination.items)
    total_weight_sum = sum(float(o.total_weight) for o in pagination.items)
    total_amount_sum = sum(float(o.total_amount) for o in pagination.items)
    default_date_start = (date_type.today() - timedelta(days=30)).isoformat()
    return render_template('sales/list.html', pagination=pagination, customers=units, departments=departments,
                           total_qty_sum=total_qty_sum, total_weight_sum=total_weight_sum, total_amount_sum=total_amount_sum,
                           default_date_start=default_date_start)


@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'GET':
        units_q = Unit.query.all()
        departments = Department.query.all()
        warehouses = Warehouse.query.all()
        return render_template('sales/form.html', customers=units_q, departments=departments, warehouses=warehouses, today=date_type.today().isoformat())

    customer_id = request.form.get('customer_id', 0, type=int)
    dept_id = request.form.get('dept_id', 0, type=int)
    warehouse_id = request.form.get('warehouse_id', 0, type=int)
    remark = request.form.get('remark', '')
    order_date_str = request.form.get('order_date', '')
    order_date_val = date_type.fromisoformat(order_date_str) if order_date_str else date_type.today()

    card_nos = request.form.getlist('card_no[]')
    product_names = request.form.getlist('product_name[]')
    brands = request.form.getlist('brand[]')
    origins = request.form.getlist('origin[]')
    specs = request.form.getlist('spec[]')
    qtys = request.form.getlist('qty[]')
    weights = request.form.getlist('weight[]')
    unit_prices = request.form.getlist('unit_price[]')
    split_qtys = request.form.getlist('split_qty[]')
    split_weights = request.form.getlist('split_weight[]')
    remarks = request.form.getlist('remark[]')
    original_card_nos = request.form.getlist('original_card_no[]')

    items_data = []
    all_warehouses = {w.id: w.name for w in Warehouse.query.all()}
    wh_name = all_warehouses.get(warehouse_id, '') if warehouse_id else ''
    for i in range(len(card_nos)):
        item = {
            'card_no': card_nos[i],
            'product_name': product_names[i],
            'brand': brands[i],
            'origin': origins[i],
            'spec': specs[i],
            'qty': int(qtys[i]),
            'weight': float(weights[i]),
            'unit_price': float(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else 0,
            'remark': remarks[i] if i < len(remarks) else '',
            'warehouse_name': wh_name
        }
        if i < len(split_qtys) and split_qtys[i]:
            item['split_qty'] = int(split_qtys[i])
        if i < len(split_weights) and split_weights[i]:
            item['split_weight'] = float(split_weights[i])
        if i < len(original_card_nos) and original_card_nos[i]:
            item['original_card_no'] = original_card_nos[i]
        items_data.append(item)

    order_data = {
        'customer_id': customer_id,
        'dept_id': dept_id,
        'remark': remark,
        'order_date': order_date_val,
        'operator_id': current_user.id
    }
    create_sales_order(order_data, items_data)
    flash('出库单创建成功', 'success')
    return redirect(url_for('sales.index'))


@sales_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    order = SalesOrder.query.get_or_404(id)
    return render_template('sales/form.html', order=order, readonly=True)


@sales_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    order = SalesOrder.query.get_or_404(id)
    if request.method == 'GET':
        units_q = Unit.query.all()
        departments = Department.query.all()
        warehouses = Warehouse.query.all()
        return render_template('sales/form.html', order=order, customers=units_q, departments=departments, warehouses=warehouses, edit_mode=True)

    for item in order.items:
        if item.split_qty and item.split_qty > 0:
            orig_card_no = re.sub(r'-\d+$', '', item.card_no)
            orig_inv = Inventory.query.filter_by(card_no=orig_card_no).first()
            if orig_inv:
                orig_inv.qty += item.split_qty
                orig_inv.weight = round(float(orig_inv.weight) + float(item.split_weight), 3)
                orig_inv.status = 'in_stock'
            TransactionLog.query.filter_by(card_no=orig_card_no, order_no=order.order_no).delete()
            split_inv = Inventory.query.filter_by(card_no=item.card_no).first()
            if split_inv:
                db.session.delete(split_inv)
        else:
            inv = Inventory.query.filter_by(card_no=item.card_no).first()
            if inv:
                inv.status = 'in_stock'
        TransactionLog.query.filter_by(card_no=item.card_no, order_no=order.order_no).delete()
    for item in order.items:
        db.session.delete(item)

    order.customer_id = request.form.get('customer_id', 0, type=int)
    order.dept_id = request.form.get('dept_id', 0, type=int)
    order.remark = request.form.get('remark', '')
    order_date_str = request.form.get('order_date', '')
    if order_date_str:
        order.order_date = date_type.fromisoformat(order_date_str)

    card_nos = request.form.getlist('card_no[]')
    product_names = request.form.getlist('product_name[]')
    brands_list = request.form.getlist('brand[]')
    origins_list = request.form.getlist('origin[]')
    specs = request.form.getlist('spec[]')
    qtys = request.form.getlist('qty[]')
    weights = request.form.getlist('weight[]')
    unit_prices = request.form.getlist('unit_price[]')
    split_qtys = request.form.getlist('split_qty[]')
    split_weights = request.form.getlist('split_weight[]')
    remarks = request.form.getlist('remark[]')
    original_card_nos = request.form.getlist('original_card_no[]')
    warehouse_id = request.form.get('warehouse_id', 0, type=int)
    all_warehouses = {w.id: w.name for w in Warehouse.query.all()}
    wh_name = all_warehouses.get(warehouse_id, '') if warehouse_id else ''

    total_qty = 0
    total_weight = 0
    total_amount = 0

    for i in range(len(card_nos)):
        unit_price = float(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else 0
        split_qty = int(split_qtys[i]) if i < len(split_qtys) and split_qtys[i] else 0
        split_weight = float(split_weights[i]) if i < len(split_weights) and split_weights[i] else 0
        shipped_qty = split_qty if split_qty else int(qtys[i])
        shipped_weight = split_weight if split_weight else float(weights[i])
        calc_weight = split_weight if split_weight > 0 else float(weights[i])
        amount = calc_weight * unit_price
        orig_card = original_card_nos[i] if i < len(original_card_nos) and original_card_nos[i] else card_nos[i]
        if split_qty and split_qty > 0:
            orig_card = re.sub(r'-\d+$', '', card_nos[i])
        si = SalesItem(
            order_id=order.id,
            card_no=card_nos[i],
            product_name=product_names[i],
            brand=brands_list[i],
            origin=origins_list[i],
            spec=specs[i],
            qty=int(qtys[i]),
            weight=float(weights[i]),
            split_qty=split_qty,
            split_weight=split_weight,
            unit_price=unit_price,
            amount=amount,
            remark=remarks[i] if i < len(remarks) else ''
        )
        db.session.add(si)

        inv = Inventory.query.filter_by(card_no=orig_card).first()
        if inv:
            si.warehouse = wh_name if wh_name else (inv.warehouse.name if inv.warehouse else '')
            if split_qty and split_qty > 0:
                if card_nos[i] != orig_card:
                    new_inv = Inventory(
                        card_no=card_nos[i],
                        product_name=product_names[i],
                        brand=brands_list[i],
                        origin=origins_list[i],
                        spec=specs[i],
                        qty=split_qty,
                        weight=split_weight,
                        warehouse_id=inv.warehouse_id,
                        dept_id=inv.dept_id,
                        status='out'
                    )
                    db.session.add(new_inv)
                weight_before = float(inv.weight)
                inv.qty -= split_qty
                inv.weight = round(float(inv.weight) - split_weight, 3)
                if inv.qty <= 0:
                    inv.status = 'out'
                tlog = TransactionLog(
                    card_no=card_nos[i],
                    type='out',
                    product_name=product_names[i],
                    spec=specs[i],
                    brand=brands_list[i],
                    origin=origins_list[i],
                    order_no=order.order_no,
                    weight_before=weight_before,
                    weight_after=float(inv.weight)
                )
                db.session.add(tlog)
            else:
                inv.status = 'out'
                tlog = TransactionLog(
                    card_no=card_nos[i],
                    type='out',
                    product_name=product_names[i],
                    spec=specs[i],
                    brand=brands_list[i],
                    origin=origins_list[i],
                    order_no=order.order_no,
                    weight_before=float(inv.weight),
                    weight_after=0
                )
                db.session.add(tlog)

        total_qty += shipped_qty
        total_weight += shipped_weight
        total_amount += amount

    order.total_qty = total_qty
    order.total_weight = total_weight
    order.total_amount = total_amount
    db.session.commit()
    flash('出库单更新成功', 'success')
    return redirect(url_for('sales.detail', id=order.id))


@sales_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    order = SalesOrder.query.get_or_404(id)
    for item in order.items:
        if item.split_qty and item.split_qty > 0:
            orig_card_no = re.sub(r'-\d+$', '', item.card_no)
            orig_inv = Inventory.query.filter_by(card_no=orig_card_no).first()
            if orig_inv:
                orig_inv.qty += item.split_qty
                orig_inv.weight = round(float(orig_inv.weight) + float(item.split_weight), 3)
                orig_inv.status = 'in_stock'
            TransactionLog.query.filter_by(card_no=orig_card_no, order_no=order.order_no).delete()
            split_inv = Inventory.query.filter_by(card_no=item.card_no).first()
            if split_inv:
                db.session.delete(split_inv)
        else:
            inv = Inventory.query.filter_by(card_no=item.card_no).first()
            if inv:
                inv.status = 'in_stock'
        TransactionLog.query.filter_by(card_no=item.card_no, order_no=order.order_no).delete()
    db.session.delete(order)
    db.session.commit()
    flash('出库单已删除', 'success')
    return redirect(url_for('sales.index'))


@sales_bp.route('/search-card')
@login_required
def search_card():
    q = request.args.get('q', '')
    results = Inventory.query.filter(
        Inventory.card_no.contains(q),
        Inventory.status == 'in_stock'
    ).limit(10).all()
    return render_template('sales/_card_search_results.html', results=results)


@sales_bp.route('/inventory-list')
@login_required
def inventory_list():
    card_no = request.args.get('card_no', '')
    product_name = request.args.get('product_name', '')
    brand = request.args.get('brand', '')
    origin = request.args.get('origin', '')
    dept_id = request.args.get('dept_id', 0, type=int)
    exclude_cards = request.args.getlist('exclude')
    query = Inventory.query.filter_by(status='in_stock')
    if card_no:
        query = query.filter(Inventory.card_no.contains(card_no))
    if product_name:
        query = query.filter(Inventory.product_name.contains(product_name))
    if brand:
        query = query.filter(Inventory.brand.contains(brand))
    if origin:
        query = query.filter(Inventory.origin.contains(origin))
    if dept_id:
        query = query.filter(Inventory.dept_id == dept_id)
    if exclude_cards:
        query = query.filter(~Inventory.card_no.in_(exclude_cards))
    results = query.order_by(Inventory.card_no).limit(200).all()
    product_names = ProductName.query.all()
    brands = Brand.query.all()
    origins = Origin.query.all()
    return render_template('sales/_inventory_modal.html', results=results, product_names=product_names, brands=brands, origins=origins)


@sales_bp.route('/detail-list')
@login_required
def detail_list():
    page = request.args.get('page', 1, type=int)
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    order_no = request.args.get('order_no', '').strip()
    customer_name = request.args.get('customer_name', '').strip()
    card_no = request.args.get('card_no', '').strip()
    spec = request.args.get('spec', '').strip()
    remark_contains = request.args.get('remark', '').strip()
    dept_id = request.args.get('dept_id', 0, type=int)
    search_submitted = request.args.get('search_submitted', '')

    query = SalesItem.query.join(SalesOrder)
    if date_start:
        query = query.filter(SalesOrder.order_date >= date_start)
    if date_end:
        query = query.filter(SalesOrder.order_date <= date_end)
    if order_no:
        query = query.filter(SalesOrder.order_no.contains(order_no))
    if customer_name:
        query = query.join(Unit, SalesOrder.customer_id == Unit.id).filter(Unit.name.contains(customer_name))
    if card_no:
        query = query.filter(SalesItem.card_no.contains(card_no))
    if spec:
        query = query.filter(SalesItem.spec.contains(spec))
    if remark_contains:
        query = query.filter(SalesItem.remark.contains(remark_contains))
    if dept_id:
        query = query.filter(SalesOrder.dept_id == dept_id)

    is_export = request.args.get('export', '') == '1'
    default_date_start = (date_type.today() - timedelta(days=30)).isoformat()
    if not search_submitted and not is_export:
        units_q = Unit.query.all()
        departments = Department.query.all()
        return render_template('sales/detail_list.html', pagination=None, customers=units_q, departments=departments,
                               search_submitted=False, default_date_start=default_date_start)

    pagination = query.order_by(SalesOrder.order_date.desc(), SalesItem.id.desc()).paginate(
        page=page, per_page=current_app.config['PER_PAGE'], error_out=False
    )

    if is_export:
        all_items = query.order_by(SalesOrder.order_date.desc(), SalesItem.id.desc()).all()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '出库明细'
        headers = ['单号', '业务日期', '客户', '销售部门', '卡号', '品名', '牌号', '产地', '规格', '仓库', '出库件数', '出库吨位', '备注', '主单备注']
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            ws.cell(row=1, column=col).font = openpyxl.styles.Font(bold=True)
        for item in all_items:
            ws.append([
                item.order.order_no,
                item.order.order_date.strftime('%Y-%m-%d') if item.order.order_date else '',
                item.order.customer.name if item.order.customer else '',
                item.order.dept.name if item.order.dept else '',
                item.card_no,
                item.product_name,
                item.brand,
                item.origin,
                item.spec,
                item.warehouse or '',
                item.split_qty if item.split_qty > 0 else item.qty,
                float(item.split_weight) if item.split_weight > 0 else float(item.weight),
                item.remark or '',
                item.order.remark or '',
            ])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='出库明细.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    units = Unit.query.all()
    departments = Department.query.all()
    def _shipped_qty(i): return i.split_qty if i.split_qty > 0 else i.qty
    def _shipped_weight(i): return float(i.split_weight) if i.split_weight > 0 else float(i.weight)
    total_qty_sum = sum(_shipped_qty(i) for i in pagination.items)
    total_weight_sum = sum(_shipped_weight(i) for i in pagination.items)
    total_amount_sum = sum(float(i.amount) for i in pagination.items)
    return render_template('sales/detail_list.html', pagination=pagination, customers=units, departments=departments,
                           search_submitted=True, total_qty_sum=total_qty_sum, total_weight_sum=total_weight_sum,
                           total_amount_sum=total_amount_sum, default_date_start=default_date_start)


@sales_bp.route('/print/<int:id>/<template_type>')
@login_required
def print_view(id, template_type):
    if template_type not in ('delivery', 'invoice'):
        abort(404)
    order = SalesOrder.query.get_or_404(id)
    page_size = 8
    batches = [order.items[i:i+page_size] for i in range(0, len(order.items), page_size)]
    if not batches:
        batches = [[]]
    return render_template(f'sales/print_{template_type}.html',
                           order=order, batches=batches)
