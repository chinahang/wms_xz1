from datetime import date

from flask import render_template
from flask_login import login_required

from app import db
from app.dashboard import dashboard_bp
from app.models import Inventory, PurchaseOrder, SalesOrder, TransactionLog


@dashboard_bp.route('/')
@login_required
def index():
    stock_qty = Inventory.query.filter_by(status='in_stock').count()
    stock_weight = db.session.query(db.func.sum(Inventory.weight)).filter(
        Inventory.status == 'in_stock'
    ).scalar() or 0

    today = date.today()
    today_in_orders = PurchaseOrder.query.filter(
        db.func.date(PurchaseOrder.created_at) == today
    ).all()
    today_in_qty = sum(o.total_qty for o in today_in_orders)
    today_in_weight = sum(float(o.total_weight) for o in today_in_orders)

    today_out_orders = SalesOrder.query.filter(
        db.func.date(SalesOrder.created_at) == today
    ).all()
    today_out_qty = sum(o.total_qty for o in today_out_orders)
    today_out_weight = sum(float(o.total_weight) for o in today_out_orders)

    recent_logs = TransactionLog.query.order_by(
        TransactionLog.created_at.desc()
    ).limit(10).all()

    return render_template('dashboard/index.html',
                           stock_qty=stock_qty,
                           stock_weight=float(stock_weight),
                           today_in_qty=today_in_qty,
                           today_in_weight=today_in_weight,
                           today_out_qty=today_out_qty,
                           today_out_weight=today_out_weight,
                           recent_logs=recent_logs)
