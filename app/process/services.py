from datetime import datetime
from app import db
from app.models import ProcessOrder, ProcessDetail, Inventory, TransactionLog


def generate_order_no():
    prefix = 'JG' + datetime.now().strftime('%Y%m%d')
    last = ProcessOrder.query.filter(ProcessOrder.order_no.like(prefix + '%')).order_by(ProcessOrder.order_no.desc()).first()
    if last:
        num = int(last.order_no[-4:]) + 1
    else:
        num = 1
    return prefix + str(num).zfill(4)


def get_inventory_by_card(card_no):
    return Inventory.query.filter_by(card_no=card_no, status='in_stock').first()


def create_process_order(order_data, details_data):
    order_no = generate_order_no()
    order = ProcessOrder(
        order_no=order_no,
        dept_id=order_data['dept_id'],
        order_date=order_data.get('order_date'),
        operator_id=order_data['operator_id']
    )
    db.session.add(order)
    db.session.flush()

    total_qty = 0
    total_weight = 0

    for detail in details_data:
        pd = ProcessDetail(
            order_id=order.id,
            raw_card_no=detail['raw_card_no'],
            raw_spec=detail['raw_spec'],
            new_card_no=detail['new_card_no'],
            product_name=detail['product_name'],
            brand=detail['brand'],
            origin=detail['origin'],
            spec=detail['spec'],
            qty=detail['qty'],
            weight=detail['weight'],
            loss_weight=detail.get('loss_weight', 0)
        )
        db.session.add(pd)

        total_qty += detail['qty']
        total_weight += detail['weight']

    order.total_qty = total_qty
    order.total_weight = total_weight

    raw_card_no = details_data[0]['raw_card_no']
    raw_inventory = Inventory.query.filter_by(card_no=raw_card_no, status='in_stock').first()
    if raw_inventory:
        raw_inventory.status = 'consumed'

    for detail in details_data:
        inv = Inventory(
            card_no=detail['new_card_no'],
            product_name=detail['product_name'],
            brand=detail['brand'],
            origin=detail['origin'],
            spec=detail['spec'],
            warehouse_id=detail.get('warehouse_id'),
            qty=detail['qty'],
            weight=detail['weight'],
            dept_id=order_data['dept_id'],
            status='in_stock'
        )
        db.session.add(inv)

    if raw_inventory:
        tlog_raw = TransactionLog(
            card_no=raw_card_no,
            type='process',
            product_name=raw_inventory.product_name,
            spec=raw_inventory.spec,
            brand=raw_inventory.brand,
            origin=raw_inventory.origin,
            order_no=order_no,
            weight_before=raw_inventory.weight,
            weight_after=0
        )
        db.session.add(tlog_raw)

    for detail in details_data:
        tlog_product = TransactionLog(
            card_no=detail['new_card_no'],
            type='process',
            product_name=detail['product_name'],
            spec=detail['spec'],
            brand=detail['brand'],
            origin=detail['origin'],
            order_no=order_no,
            weight_before=0,
            weight_after=detail['weight']
        )
        db.session.add(tlog_product)

    db.session.commit()
    return order
