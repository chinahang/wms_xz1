from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_session import Session

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
csrf = CSRFProtect()


def create_app(config_name='development'):
    from config import config_map

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name))

    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.purchase import purchase_bp
    from app.process import process_bp
    from app.sales import sales_bp
    from app.inventory import inventory_bp
    from app.report import report_bp
    from app.base_data import base_data_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(purchase_bp, url_prefix='/purchase')
    app.register_blueprint(process_bp, url_prefix='/process')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(report_bp, url_prefix='/report')
    app.register_blueprint(base_data_bp, url_prefix='/base-data')

    return app
