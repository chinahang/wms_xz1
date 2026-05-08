from flask import Blueprint

base_data_bp = Blueprint('base_data', __name__)

from app.base_data import routes
