# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # relationship to doctors via users.department_id FK
    doctors = db.relationship('User', backref='department', lazy='dynamic')

    def __repr__(self):
        return f"<Department id={self.id} name={self.name}>"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'doctor', 'patient'
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=True)
    contact = db.Column(db.String(50), nullable=True)

    # normalized relation to department
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    # an optional free-text specialization label (not used as a FK)
    specialization = db.Column(db.String(120), nullable=True)

    # patient-specific
    age = db.Column(db.Integer, nullable=True)

    def is_admin(self):
        return self.role == 'admin'

    def is_doctor(self):
        return self.role == 'doctor'

    def is_patient(self):
        return self.role == 'patient'

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"

class Availability(db.Model):
    __tablename__ = 'availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    doctor = db.relationship('User', backref=db.backref('availabilities', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Availability id={self.id} doctor_id={self.doctor_id} date={self.date}>"

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)  # start time
    status = db.Column(db.String(20), default='Booked')  # Booked, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('appointments_as_patient', cascade='all, delete-orphan'))
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref=db.backref('appointments_as_doctor', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Appointment id={self.id} patient_id={self.patient_id} doctor_id={self.doctor_id} date={self.date} time={self.time}>"

class Treatment(db.Model):
    __tablename__ = 'treatments'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    appointment = db.relationship('Appointment', backref=db.backref('treatments', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Treatment id={self.id} appointment_id={self.appointment_id}>"
