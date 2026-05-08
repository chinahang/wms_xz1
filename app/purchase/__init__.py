from flask import Blueprint

purchase_bp = Blueprint('purchase', __name__)

from app.purchase import routes
