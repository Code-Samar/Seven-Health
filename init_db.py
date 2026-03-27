import os
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()

    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin_name = os.environ.get('ADMIN_NAME', 'Hospital Admin')

    # create an admin if not exists
    if not User.query.filter_by(username=admin_username).first():
        admin = User(
            username=admin_username,
            password_hash=generate_password_hash(admin_password),
            role='admin',
            name=admin_name
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user created: username={admin_username}')
    else:
        print('Admin already exists')
