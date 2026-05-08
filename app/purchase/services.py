from datetime import datetime
from app import db
from app.models import PurchaseOrder, PurchaseItem, Inventory, TransactionLog


def generate_order_no():
    prefix = 'RK' + datetime.now().strftime('%Y%m%d')
    last = PurchaseOrder.query.filter(PurchaseOrder.order_no.like(prefix + '%')).order_by(PurchaseOrder.order_no.desc()).first()
    if last:
        num = int(last.order_no[-4:]) + 1
    else:
        num = 1
    return prefix + str(num).zfill(4)


def create_purchase_order(order_data, items_data):
    order_no = generate_order_no()
    order = PurchaseOrder(
        order_no=order_no,
        supplier_id=order_data['supplier_id'],
        dept_id=order_data['dept_id'],
        remark=order_data.get('remark', ''),
        order_date=order_data.get('order_date'),
        operator_id=order_data['operator_id']
    )
    db.session.add(order)
    db.session.flush()

    total_qty = 0
    total_weight = 0
    total_amount = 0

    for item in items_data:
        unit_price = item.get('unit_price', 0) or 0
        amount = float(item['weight']) * float(unit_price)
        pi = PurchaseItem(
            order_id=order.id,
            card_no=item['card_no'],
            product_name=item['product_name'],
            brand=item['brand'],
            origin=item['origin'],
            spec=item['spec'],
            qty=item['qty'],
            weight=item['weight'],
            unit_price=unit_price,
            amount=amount,
            warehouse=item.get('warehouse', ''),
            remark=item.get('remark', '')
        )
        db.session.add(pi)

        inv = Inventory(
            card_no=item['card_no'],
            product_name=item['product_name'],
            brand=item['brand'],
            origin=item['origin'],
            spec=item['spec'],
            warehouse_id=item.get('warehouse_id'),
            qty=item['qty'],
            weight=item['weight'],
            dept_id=order_data['dept_id'],
            status='in_stock'
        )
        db.session.add(inv)

        tlog = TransactionLog(
            card_no=item['card_no'],
            type='in',
            product_name=item['product_name'],
            spec=item['spec'],
            brand=item['brand'],
            origin=item['origin'],
            order_no=order_no,
            weight_before=0,
            weight_after=item['weight']
        )
        db.session.add(tlog)

        total_qty += item['qty']
        total_weight += item['weight']
        total_amount += amount

    order.total_qty = total_qty
    order.total_weight = total_weight
    order.total_amount = total_amount
    db.session.commit()
    return order
