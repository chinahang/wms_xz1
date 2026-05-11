from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.process import process_bp
from app.process.services import create_process_order
from app.models import ProcessOrder, ProcessDetail, Department, ProductName, Brand, Origin, Inventory, TransactionLog, CalcSpec, SalesItem, Warehouse
from app import db
from datetime import date as date_type
import openpyxl
from io import BytesIO


@process_bp.route('/')
@login_required
def index():
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    dept_id = request.args.get('dept_id', 0, type=int)
    search_submitted = request.args.get('search_submitted', '')

    if not search_submitted:
        departments = Department.query.all()
        return render_template('process/list.html', items=[], departments=departments, search_submitted=False,
                               total_qty_sum=0, total_weight_sum=0)

    query = ProcessOrder.query
    if date_start:
        query = query.filter(ProcessOrder.order_date >= date_start)
    if date_end:
        query = query.filter(ProcessOrder.order_date <= date_end)
    if dept_id:
        query = query.filter(ProcessOrder.dept_id == dept_id)

    departments = Department.query.all()
    items = query.order_by(ProcessOrder.order_date.desc(), ProcessOrder.created_at.desc()).all()
    departments = Department.query.all()
    total_qty_sum = sum(o.total_qty for o in items)
    total_weight_sum = sum(float(o.total_weight) for o in items)
    return render_template('process/list.html', items=items, departments=departments,
                           total_qty_sum=total_qty_sum, total_weight_sum=total_weight_sum)


@process_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'GET':
        departments = Department.query.all()
        product_names = ProductName.query.all()
        brands = Brand.query.all()
        origins = Origin.query.all()
        calc_specs = CalcSpec.query.filter_by(enabled=True).all()
        calc_enabled_names = [cs.product_name.name for cs in calc_specs]
        return render_template('process/form.html', departments=departments, product_names=product_names, brands=brands, origins=origins, today=date_type.today().isoformat(), calc_enabled_names=calc_enabled_names)

    dept_id = request.form.get('dept_id', 0, type=int)
    raw_card_no = request.form.get('raw_card_no', '')
    raw_spec = request.form.get('raw_spec', '')
    remark = request.form.get('remark', '')
    order_date_str = request.form.get('order_date', '')
    order_date_val = date_type.fromisoformat(order_date_str) if order_date_str else date_type.today()

    new_card_nos = request.form.getlist('new_card_no[]')
    product_names = request.form.getlist('product_name[]')
    brands = request.form.getlist('brand[]')
    origins = request.form.getlist('origin[]')
    specs = request.form.getlist('spec[]')
    qtys = request.form.getlist('qty[]')
    weights = request.form.getlist('weight[]')
    loss_weights = request.form.getlist('loss_weight[]')
    wh_names = request.form.getlist('warehouse[]')
    wh_map = {w.name: w.id for w in Warehouse.query.all()}

    details_data = []
    for i in range(len(new_card_nos)):
        wh_id = wh_map.get(wh_names[i]) if i < len(wh_names) and wh_names[i] else None
        details_data.append({
            'raw_card_no': raw_card_no,
            'raw_spec': raw_spec,
            'new_card_no': new_card_nos[i],
            'product_name': product_names[i],
            'brand': brands[i],
            'origin': origins[i],
            'spec': specs[i],
            'qty': int(qtys[i]),
            'weight': float(weights[i]),
            'loss_weight': float(loss_weights[i]) if i < len(loss_weights) and loss_weights[i] else 0,
            'warehouse_id': wh_id,
            'warehouse': wh_names[i] if i < len(wh_names) else ''
        })

    order_data = {
        'dept_id': dept_id,
        'order_date': order_date_val,
        'operator_id': current_user.id
    }
    create_process_order(order_data, details_data)
    flash('加工单创建成功', 'success')
    return redirect(url_for('process.index'))


@process_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    order = ProcessOrder.query.get_or_404(id)
    raw_detail = order.details[0] if order.details else None
    raw_inv = Inventory.query.filter_by(card_no=raw_detail.raw_card_no).first() if raw_detail else None
    return render_template('process/form.html', order=order, raw_inventory=raw_inv, readonly=True)


@process_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    order = ProcessOrder.query.get_or_404(id)
    if request.method == 'GET':
        departments = Department.query.all()
        product_names = ProductName.query.all()
        brands = Brand.query.all()
        origins = Origin.query.all()
        calc_specs = CalcSpec.query.filter_by(enabled=True).all()
        calc_enabled_names = [cs.product_name.name for cs in calc_specs]
        raw_detail = order.details[0] if order.details else None
        raw_inv = Inventory.query.filter_by(card_no=raw_detail.raw_card_no).first() if raw_detail else None
        raw_weight = float(raw_inv.weight) if raw_inv else 0
        return render_template('process/form.html', order=order, departments=departments,
                               product_names=product_names, brands=brands, origins=origins,
                                raw_inventory=raw_inv, raw_weight=raw_weight,
                                edit_mode=True, calc_enabled_names=calc_enabled_names)

    for detail in order.details:
        si = SalesItem.query.filter_by(card_no=detail.new_card_no).first()
        if si:
            flash('该加工单的产出' + detail.new_card_no + '已被出库使用，请先删除出库单', 'error')
            return redirect(url_for('process.detail', id=order.id))

    raw_card_no = order.details[0].raw_card_no if order.details else None
    if raw_card_no:
        raw_inv = Inventory.query.filter_by(card_no=raw_card_no, status='consumed').first()
        if raw_inv:
            raw_inv.status = 'in_stock'
    for detail in order.details:
        new_inv = Inventory.query.filter_by(card_no=detail.new_card_no).first()
        if new_inv:
            db.session.delete(new_inv)
    TransactionLog.query.filter_by(order_no=order.order_no).delete()
    for detail in order.details:
        db.session.delete(detail)

    order.dept_id = request.form.get('dept_id', 0, type=int)
    order_date_str = request.form.get('order_date', '')
    if order_date_str:
        order.order_date = date_type.fromisoformat(order_date_str)

    raw_card_no = request.form.get('raw_card_no', '')
    raw_spec = request.form.get('raw_spec', '')

    new_card_nos = request.form.getlist('new_card_no[]')
    product_names = request.form.getlist('product_name[]')
    brands_list = request.form.getlist('brand[]')
    origins_list = request.form.getlist('origin[]')
    specs = request.form.getlist('spec[]')
    qtys = request.form.getlist('qty[]')
    weights = request.form.getlist('weight[]')
    raw_specs = request.form.getlist('raw_spec[]')
    loss_weights = request.form.getlist('loss_weight[]')
    wh_names = request.form.getlist('warehouse[]')
    wh_map = {w.name: w.id for w in Warehouse.query.all()}

    total_qty = 0
    total_weight = 0

    for i in range(len(new_card_nos)):
        wh_id = wh_map.get(wh_names[i]) if i < len(wh_names) and wh_names[i] else None
        pd = ProcessDetail(
            order_id=order.id,
            raw_card_no=raw_card_no,
            raw_spec=raw_specs[i] if i < len(raw_specs) else raw_spec,
            new_card_no=new_card_nos[i],
            product_name=product_names[i],
            brand=brands_list[i],
            origin=origins_list[i],
            spec=specs[i],
            qty=int(qtys[i]),
            weight=float(weights[i]),
            loss_weight=float(loss_weights[i]) if i < len(loss_weights) and loss_weights[i] else 0
        )
        db.session.add(pd)

        new_inv = Inventory(
            card_no=new_card_nos[i],
            product_name=product_names[i],
            brand=brands_list[i],
            origin=origins_list[i],
            spec=specs[i],
            qty=int(qtys[i]),
            weight=float(weights[i]),
            warehouse_id=wh_id,
            dept_id=order.dept_id,
            status='in_stock'
        )
        db.session.add(new_inv)

        tlog = TransactionLog(
            card_no=new_card_nos[i],
            type='process',
            product_name=product_names[i],
            spec=specs[i],
            brand=brands_list[i],
            origin=origins_list[i],
            order_no=order.order_no,
            weight_before=0,
            weight_after=float(weights[i])
        )
        db.session.add(tlog)

        total_qty += int(qtys[i])
        total_weight += float(weights[i])

    if raw_card_no:
        raw_inv = Inventory.query.filter_by(card_no=raw_card_no, status='in_stock').first()
        if raw_inv:
            raw_inv.status = 'consumed'

    order.total_qty = total_qty
    order.total_weight = total_weight
    db.session.commit()
    flash('加工单更新成功', 'success')
    return redirect(url_for('process.detail', id=order.id))


@process_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    order = ProcessOrder.query.get_or_404(id)
    for detail in order.details:
        si = SalesItem.query.filter_by(card_no=detail.new_card_no).first()
        if si:
            flash('该加工单的产出' + detail.new_card_no + '已被出库使用，请先删除出库单', 'error')
            return redirect(url_for('process.index'))
    raw_card_no = order.details[0].raw_card_no if order.details else None
    if raw_card_no:
        raw_inv = Inventory.query.filter_by(card_no=raw_card_no, status='consumed').first()
        if raw_inv:
            raw_inv.status = 'in_stock'
    for detail in order.details:
        inv = Inventory.query.filter_by(card_no=detail.new_card_no).first()
        if inv:
            db.session.delete(inv)
    TransactionLog.query.filter_by(order_no=order.order_no).delete()
    db.session.delete(order)
    db.session.commit()
    flash('加工单已删除', 'success')
    return redirect(url_for('process.index'))


@process_bp.route('/search-card')
@login_required
def search_card():
    q = request.args.get('q', '')
    results = Inventory.query.filter(
        Inventory.card_no.contains(q),
        Inventory.status == 'in_stock'
    ).limit(10).all()
    return render_template('process/_card_search_results.html', results=results)


@process_bp.route('/inventory-modal')
@login_required
def inventory_modal():
    dept_id = request.args.get('dept_id', 0, type=int)
    card_no = request.args.get('card_no', '')
    product_name = request.args.get('product_name', '')
    brands = request.args.get('brand', '')
    origin = request.args.get('origin', '')
    query = Inventory.query.filter_by(status='in_stock')
    if dept_id:
        query = query.filter(Inventory.dept_id == dept_id)
    if card_no:
        query = query.filter(Inventory.card_no.contains(card_no))
    if product_name:
        query = query.filter(Inventory.product_name.contains(product_name))
    if brands:
        query = query.filter(Inventory.brand.contains(brands))
    if origin:
        query = query.filter(Inventory.origin.contains(origin))
    results = query.order_by(Inventory.card_no).limit(200).all()
    pns = ProductName.query.all()
    brand_list = Brand.query.all()
    origin_list = Origin.query.all()
    return render_template('sales/_inventory_modal.html', results=results, product_names=pns, brands=brand_list, origins=origin_list)


@process_bp.route('/detail-list')
@login_required
def detail_list():
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    dept_id = request.args.get('dept_id', 0, type=int)
    search_submitted = request.args.get('search_submitted', '')

    query = ProcessDetail.query.join(ProcessOrder)
    if date_start:
        query = query.filter(ProcessOrder.order_date >= date_start)
    if date_end:
        query = query.filter(ProcessOrder.order_date <= date_end)
    if dept_id:
        query = query.filter(ProcessOrder.dept_id == dept_id)

    is_export = request.args.get('export', '') == '1'
    if not search_submitted and not is_export:
        departments = Department.query.all()
        return render_template('process/detail_list.html', items=[], departments=departments, search_submitted=False)

    items = query.order_by(ProcessOrder.order_date.desc(), ProcessDetail.id.desc()).all()

    if is_export:
        all_details = query.order_by(ProcessOrder.order_date.desc(), ProcessDetail.id.desc()).all()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '加工明细'
        headers = ['单号', '业务日期', '销售部门', '原料卡号', '原料规格', '新卡号', '品名', '牌号', '产地', '规格', '件数', '吨位', '损耗']
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            ws.cell(row=1, column=col).font = openpyxl.styles.Font(bold=True)
        for d in all_details:
            ws.append([
                d.order.order_no,
                d.order.order_date.strftime('%Y-%m-%d') if d.order.order_date else '',
                d.order.dept.name if d.order.dept else '',
                d.raw_card_no,
                d.raw_spec,
                d.new_card_no,
                d.product_name,
                d.brand,
                d.origin,
                d.spec,
                d.qty,
                float(d.weight),
                float(d.loss_weight),
            ])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='加工明细.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    departments = Department.query.all()
    total_qty_sum = sum(d.qty for d in items)
    total_weight_sum = sum(float(d.weight) for d in items)
    total_loss_sum = sum(float(d.loss_weight) for d in items)
    return render_template('process/detail_list.html', items=items, departments=departments,
                           search_submitted=True,
                           total_qty_sum=total_qty_sum, total_weight_sum=total_weight_sum, total_loss_sum=total_loss_sum)
