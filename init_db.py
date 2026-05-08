from app import create_app, db
from app.models import User, ProductName, Brand, Origin, Department, Unit
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_active=True
        )
        db.session.add(admin)

    product_names = ['热轧卷板', '冷轧板', '螺纹钢', '中厚板', '角钢', '槽钢', 'H型钢']
    for name in product_names:
        if not ProductName.query.filter_by(name=name).first():
            db.session.add(ProductName(name=name))

    brands = ['Q235B', 'Q345B', 'HRB400', 'Q235', 'Q345', 'Q195']
    for name in brands:
        if not Brand.query.filter_by(name=name).first():
            db.session.add(Brand(name=name))

    origins = ['首钢', '宝钢', '鞍钢', '沙钢', '日钢', '武钢']
    for name in origins:
        if not Origin.query.filter_by(name=name).first():
            db.session.add(Origin(name=name))

    departments = ['销售一部', '销售二部']
    for name in departments:
        if not Department.query.filter_by(name=name).first():
            db.session.add(Department(name=name))

    db.session.commit()
    print('数据库初始化完成')
