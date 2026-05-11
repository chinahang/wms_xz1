import json
from io import BytesIO
from flask import render_template, request, current_app, send_file
from flask_login import login_required
from app.report import report_bp
from app.models import (PurchaseOrder, PurchaseItem, SalesOrder, SalesItem,
                        Inventory, ProcessOrder, ProcessDetail, TransactionLog,
                        Unit, Department, Brand, Origin, ProductName)
from app import db
from openpyxl import Workbook


def export_excel(headers, rows, filename='export.xlsx'):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@report_bp.route('/purchase')
@login_required
def purchase_report():
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    supplier_id = request.args.get('supplier_id', 0, type=int)
    product_name = request.args.get('product_name', '')
    dept_id = request.args.get('dept_id', 0, type=int)

    query = db.session.query(PurchaseItem, PurchaseOrder).join(PurchaseOrder, PurchaseItem.order_id == PurchaseOrder.id)
    if date_start:
        query = query.filter(PurchaseOrder.created_at >= date_start)
    if date_end:
        query = query.filter(PurchaseOrder.created_at <= date_end + ' 23:59:59')
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if product_name:
        query = query.filter(PurchaseItem.product_name.contains(product_name))
    if dept_id:
        query = query.filter(PurchaseOrder.dept_id == dept_id)

    if request.args.get('export') == 'excel':
        results = query.order_by(PurchaseOrder.created_at.desc()).all()
        headers = ['日期', '单号', '供应商', '卡号', '品名', '牌号', '产地', '规格', '件数', '吨位']
        rows = []
        for item, order in results:
            rows.append([
                order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                order.order_no,
                order.supplier.name if order.supplier else '',
                item.card_no,
                item.product_name,
                item.brand,
                item.origin,
                item.spec,
                item.qty,
                float(item.weight)
            ])
        return export_excel(headers, rows, '入库明细报表.xlsx')

    items = query.order_by(PurchaseOrder.created_at.desc()).all()
    suppliers = Unit.query.all()
    departments = Department.query.all()
    product_names = ProductName.query.all()
    return render_template('report/purchase.html', items=items, suppliers=suppliers, departments=departments, product_names=product_names)


@report_bp.route('/sales')
@login_required
def sales_report():
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    customer_id = request.args.get('customer_id', 0, type=int)
    product_name = request.args.get('product_name', '')
    dept_id = request.args.get('dept_id', 0, type=int)

    query = db.session.query(SalesItem, SalesOrder).join(SalesOrder, SalesItem.order_id == SalesOrder.id)
    if date_start:
        query = query.filter(SalesOrder.created_at >= date_start)
    if date_end:
        query = query.filter(SalesOrder.created_at <= date_end + ' 23:59:59')
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if product_name:
        query = query.filter(SalesItem.product_name.contains(product_name))
    if dept_id:
        query = query.filter(SalesOrder.dept_id == dept_id)

    if request.args.get('export') == 'excel':
        results = query.order_by(SalesOrder.created_at.desc()).all()
        headers = ['日期', '单号', '客户', '卡号', '品名', '牌号', '产地', '规格', '件数', '吨位']
        rows = []
        for item, order in results:
            rows.append([
                order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                order.order_no,
                order.customer.name if order.customer else '',
                item.card_no,
                item.product_name,
                item.brand,
                item.origin,
                item.spec,
                item.qty,
                float(item.weight)
            ])
        return export_excel(headers, rows, '出库明细报表.xlsx')

    items = query.order_by(SalesOrder.created_at.desc()).all()
    customers = Unit.query.all()
    departments = Department.query.all()
    product_names = ProductName.query.all()
    return render_template('report/sales.html', items=items, customers=customers, departments=departments, product_names=product_names)


@report_bp.route('/inventory')
@login_required
def inventory_report():
    product_name = request.args.get('product_name', '')
    brand = request.args.get('brand', '')
    origin = request.args.get('origin', '')
    dept_id = request.args.get('dept_id', 0, type=int)

    query = db.session.query(
        Inventory.product_name,
        Inventory.brand,
        Inventory.origin,
        db.func.sum(Inventory.qty).label('total_qty'),
        db.func.sum(Inventory.weight).label('total_weight'),
        db.func.count(Inventory.id).label('count')
    ).filter(Inventory.status == 'in_stock')

    if product_name:
        query = query.filter(Inventory.product_name.contains(product_name))
    if brand:
        query = query.filter(Inventory.brand == brand)
    if origin:
        query = query.filter(Inventory.origin == origin)
    if dept_id:
        query = query.filter(Inventory.dept_id == dept_id)

    query = query.group_by(Inventory.product_name, Inventory.brand, Inventory.origin)

    if request.args.get('export') == 'excel':
        results = query.all()
        headers = ['品名', '牌号', '产地', '卡号数量', '总件数', '总吨位']
        rows = []
        for r in results:
            rows.append([r.product_name, r.brand, r.origin, r.count, float(r.total_qty or 0), float(r.total_weight or 0)])
        return export_excel(headers, rows, '库存汇总报表.xlsx')

    results = query.all()
    brands = Brand.query.all()
    origins = Origin.query.all()
    departments = Department.query.all()
    product_names = ProductName.query.all()
    return render_template('report/inventory.html', items=results, product_names=product_names, brands=brands, origins=origins, departments=departments)


@report_bp.route('/process')
@login_required
def process_report():
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    product_name = request.args.get('product_name', '')

    query = db.session.query(ProcessDetail, ProcessOrder).join(ProcessOrder, ProcessDetail.order_id == ProcessOrder.id)
    if date_start:
        query = query.filter(ProcessOrder.created_at >= date_start)
    if date_end:
        query = query.filter(ProcessOrder.created_at <= date_end + ' 23:59:59')
    if product_name:
        query = query.filter(ProcessDetail.product_name.contains(product_name))

    if request.args.get('export') == 'excel':
        results = query.order_by(ProcessOrder.created_at.desc()).all()
        headers = ['日期', '单号', '原料卡号', '原卷规格', '新卡号', '品名', '产出吨位', '损耗']
        rows = []
        for detail, order in results:
            rows.append([
                order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                order.order_no,
                detail.raw_card_no,
                detail.raw_spec,
                detail.new_card_no,
                detail.product_name,
                float(detail.weight),
                float(detail.loss_weight)
            ])
        return export_excel(headers, rows, '加工损耗报表.xlsx')

    items = query.order_by(ProcessOrder.created_at.desc()).all()
    total_input = sum(float(d.weight) + float(d.loss_weight) for d, o in items)
    total_output = sum(float(d.weight) for d, o in items)
    total_loss = sum(float(d.loss_weight) for d, o in items)
    loss_rate = total_loss / total_input if total_input > 0 else 0

    return render_template('report/process.html', items=items, total_input=total_input, total_output=total_output, total_loss=total_loss, loss_rate=loss_rate)


@report_bp.route('/custom')
@login_required
def custom_report():
    card_no = request.args.get('card_no', '')
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')

    logs = []
    chart_data = '{}'

    if card_no:
        logs = TransactionLog.query.filter_by(card_no=card_no).order_by(TransactionLog.created_at).all()

        if request.args.get('export') == 'excel':
            headers = ['时间', '类型', '卡号', '品名', '规格', '单号', '变动前吨位', '变动后吨位']
            rows = []
            for log in logs:
                rows.append([
                    log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else '',
                    log.type,
                    log.card_no,
                    log.product_name,
                    log.spec,
                    log.order_no,
                    float(log.weight_before or 0),
                    float(log.weight_after or 0)
                ])
            return export_excel(headers, rows, '自定义查询.xlsx')

    if date_start and date_end:
        date_query = db.session.query(
            db.func.date(TransactionLog.created_at).label('date'),
            TransactionLog.type,
            db.func.sum(TransactionLog.weight_after - TransactionLog.weight_before).label('total_weight')
        ).filter(
            TransactionLog.created_at >= date_start,
            TransactionLog.created_at <= date_end + ' 23:59:59'
        ).group_by(db.func.date(TransactionLog.created_at), TransactionLog.type).order_by(db.func.date(TransactionLog.created_at))

        results = date_query.all()
        dates = sorted(set(str(r.date) for r in results))
        in_data = []
        out_data = []
        for d in dates:
            in_val = sum(float(r.total_weight or 0) for r in results if str(r.date) == d and r.type == 'in')
            out_val = sum(abs(float(r.total_weight or 0)) for r in results if str(r.date) == d and r.type == 'out')
            in_data.append(round(in_val, 3))
            out_data.append(round(out_val, 3))

        chart_data = json.dumps({
            'labels': dates,
            'datasets': [
                {'label': '入库', 'data': in_data, 'borderColor': '#22c55e', 'fill': False},
                {'label': '出库', 'data': out_data, 'borderColor': '#ef4444', 'fill': False}
            ]
        })

    return render_template('report/custom.html', logs=logs, chart_data=chart_data)
