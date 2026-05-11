from flask import render_template, request, current_app
from flask_login import login_required
from app.inventory import inventory_bp
from app.models import Inventory, Department, Brand, Origin, ProductName, Warehouse, PurchaseItem, PurchaseOrder, ProcessDetail, ProcessOrder
from app import db

import re


@inventory_bp.route('/')
@login_required
def index():
    card_no = request.args.get('card_no', '')
    product_name = request.args.get('product_name', '')
    brand = request.args.get('brand', '')
    origin = request.args.get('origin', '')
    dept_id = request.args.get('dept_id', 0, type=int)
    warehouse_id = request.args.get('warehouse_id', 0, type=int)
    status = request.args.get('status', '')

    query = Inventory.query
    if card_no:
        query = query.filter(Inventory.card_no.contains(card_no))
    if product_name:
        query = query.filter(Inventory.product_name.contains(product_name))
    if brand:
        query = query.filter(Inventory.brand == brand)
    if origin:
        query = query.filter(Inventory.origin == origin)
    if dept_id:
        query = query.filter(Inventory.dept_id == dept_id)
    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    if status:
        query = query.filter(Inventory.status == status)

    items = query.order_by(Inventory.created_at.desc()).all()
    product_names = ProductName.query.all()
    brands = Brand.query.all()
    origins = Origin.query.all()
    departments = Department.query.all()
    warehouses = Warehouse.query.all()
    total_qty_sum = sum(item.qty for item in items)
    total_weight_sum = sum(float(item.weight) for item in items)
    card_nos = [item.card_no for item in items]
    purchase_dates = {}
    if card_nos:
        subq = db.session.query(
            PurchaseItem.card_no,
            db.func.min(PurchaseOrder.order_date).label('first_date')
        ).join(PurchaseOrder).group_by(PurchaseItem.card_no).subquery()
        rows = db.session.query(subq.c.card_no, subq.c.first_date).filter(
            subq.c.card_no.in_(card_nos)
        ).all()
        for r in rows:
            if r.first_date:
                purchase_dates[r.card_no] = r.first_date.strftime('%Y-%m-%d')
        p_rows = db.session.query(
            ProcessDetail.new_card_no,
            db.func.min(ProcessOrder.order_date).label('first_date')
        ).join(ProcessOrder).filter(
            ProcessDetail.new_card_no.in_(card_nos)
        ).group_by(ProcessDetail.new_card_no).all()
        for r in p_rows:
            if r.first_date:
                purchase_dates[r.new_card_no] = r.first_date.strftime('%Y-%m-%d')
        split_origins = {}
        for card_no in card_nos:
            if card_no not in purchase_dates:
                origin = re.sub(r'-\d+$', '', card_no)
                if origin != card_no:
                    split_origins[card_no] = origin
        if split_origins:
            origin_cards = list(set(split_origins.values()))
            pi_rows = db.session.query(
                PurchaseItem.card_no,
                db.func.min(PurchaseOrder.order_date).label('first_date')
            ).join(PurchaseOrder).filter(
                PurchaseItem.card_no.in_(origin_cards)
            ).group_by(PurchaseItem.card_no).all()
            for r in pi_rows:
                if r.first_date:
                    for split_card, orig_card in split_origins.items():
                        if orig_card == r.card_no:
                            purchase_dates[split_card] = r.first_date.strftime('%Y-%m-%d')
            pd_rows = db.session.query(
                ProcessDetail.new_card_no,
                db.func.min(ProcessOrder.order_date).label('first_date')
            ).join(ProcessOrder).filter(
                ProcessDetail.new_card_no.in_(origin_cards)
            ).group_by(ProcessDetail.new_card_no).all()
            for r in pd_rows:
                if r.first_date:
                    for split_card, orig_card in split_origins.items():
                        if orig_card == r.new_card_no:
                            purchase_dates[split_card] = r.first_date.strftime('%Y-%m-%d')
    return render_template('inventory/list.html', items=items, product_names=product_names, brands=brands, origins=origins, departments=departments, warehouses=warehouses,
                           total_qty_sum=total_qty_sum, total_weight_sum=total_weight_sum, purchase_dates=purchase_dates)


@inventory_bp.route('/summary')
@login_required
def summary():
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
    results = query.all()
    brands = Brand.query.all()
    origins = Origin.query.all()
    departments = Department.query.all()
    product_names = ProductName.query.all()
    total_qty_sum = sum(int(r.total_qty) for r in results)
    total_weight_sum = sum(float(r.total_weight) for r in results)
    total_count_sum = sum(int(r.count) for r in results)
    return render_template('inventory/summary.html', items=results, product_names=product_names, brands=brands, origins=origins, departments=departments,
                           total_qty_sum=total_qty_sum, total_weight_sum=total_weight_sum, total_count_sum=total_count_sum)
