from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()
    # create an admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            name='Hospital Admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: username=admin password=admin123')
    else:
        print('Admin already exists')
