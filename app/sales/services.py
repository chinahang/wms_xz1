from datetime import datetime
from app import db
from app.models import SalesOrder, SalesItem, Inventory, TransactionLog


def generate_order_no():
    prefix = 'CK' + datetime.now().strftime('%Y%m%d')
    last = SalesOrder.query.filter(SalesOrder.order_no.like(prefix + '%')).order_by(SalesOrder.order_no.desc()).first()
    if last:
        num = int(last.order_no[-4:]) + 1
    else:
        num = 1
    return prefix + str(num).zfill(4)


def create_sales_order(order_data, items_data):
    order_no = generate_order_no()
    order = SalesOrder(
        order_no=order_no,
        customer_id=order_data['customer_id'],
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
        split_qty = item.get('split_qty')
        split_weight = item.get('split_weight', 0) or 0
        shipped_qty = split_qty if split_qty else int(item['qty'])
        shipped_weight = split_weight if split_weight else float(item['weight'])
        calc_weight = split_weight if split_weight > 0 else float(item['weight'])
        amount = calc_weight * float(unit_price)
        si = SalesItem(
            order_id=order.id,
            card_no=item['card_no'],
            product_name=item['product_name'],
            brand=item['brand'],
            origin=item['origin'],
            spec=item['spec'],
            qty=item['qty'],
            weight=item['weight'],
            split_qty=split_qty or 0,
            split_weight=split_weight,
            unit_price=unit_price,
            amount=amount,
            remark=item.get('remark', '')
        )
        db.session.add(si)

        orig_card = item.get('original_card_no', item['card_no'])
        inventory = Inventory.query.filter_by(card_no=orig_card).first()
        if inventory:
            si.warehouse = item.get('warehouse_name', '') if item.get('warehouse_name') else (inventory.warehouse.name if inventory.warehouse else '')
            if split_qty and split_qty <= inventory.qty:
                if not split_weight:
                    split_weight = round((split_qty / inventory.qty) * float(inventory.weight), 3)
                if item['card_no'] != orig_card:
                    new_inv = Inventory(
                        card_no=item['card_no'],
                        product_name=item['product_name'],
                        brand=item['brand'],
                        origin=item['origin'],
                        spec=item['spec'],
                        qty=split_qty,
                        weight=split_weight,
                        warehouse_id=inventory.warehouse_id,
                        dept_id=inventory.dept_id,
                        status='out'
                    )
                    db.session.add(new_inv)
                weight_before = float(inventory.weight)
                inventory.qty -= split_qty
                inventory.weight = round(float(inventory.weight) - split_weight, 3)
                if inventory.qty <= 0:
                    inventory.status = 'out'
                si.split_qty = split_qty
                si.split_weight = split_weight
                tlog = TransactionLog(
                    card_no=item['card_no'],
                    type='out',
                    product_name=item['product_name'],
                    spec=item['spec'],
                    brand=item['brand'],
                    origin=item['origin'],
                    order_no=order_no,
                    weight_before=weight_before,
                    weight_after=float(inventory.weight)
                )
                db.session.add(tlog)
            else:
                weight_before = inventory.weight
                inventory.status = 'out'
                tlog = TransactionLog(
                    card_no=item['card_no'],
                    type='out',
                    product_name=item['product_name'],
                    spec=item['spec'],
                    brand=item['brand'],
                    origin=item['origin'],
                    order_no=order_no,
                    weight_before=weight_before,
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
    return order
