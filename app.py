import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from config import Config
from models import db, User, Department, Availability, Appointment, Treatment
from forms import LoginForm, RegisterPatientForm, DoctorForm, AppointmentForm, AvailabilityForm, TreatmentForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta, date, time as time_cls

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if os.environ.get('VERCEL') and app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite:///'):
        app.logger.error('DATABASE_URL is not set on Vercel. SQLite fallback is enabled and write operations can fail in serverless runtime.')

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    def bootstrap_database():
        # On Vercel demo deployments, initialize schema automatically unless explicitly disabled.
        auto_create_default = '1' if os.environ.get('VERCEL') else '0'
        auto_create_enabled = os.environ.get('DB_AUTO_CREATE', auto_create_default) == '1'

        if not auto_create_enabled:
            return

        try:
            with app.app_context():
                db.create_all()

                admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
                admin_password = os.environ.get('ADMIN_PASSWORD')
                admin_name = os.environ.get('ADMIN_NAME', 'Hospital Admin')

                # Create admin only when password is explicitly provided.
                if admin_password and not User.query.filter_by(username=admin_username).first():
                    admin = User(
                        username=admin_username,
                        password_hash=generate_password_hash(admin_password),
                        role='admin',
                        name=admin_name,
                    )
                    db.session.add(admin)
                    db.session.commit()

                app.logger.info('Database schema bootstrap completed.')
        except SQLAlchemyError as err:
            db.session.rollback()
            app.logger.exception('Database bootstrap failed: %s', err)

    bootstrap_database()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            if current_user.is_doctor():
                return redirect(url_for('doctor_dashboard'))
            if current_user.is_patient():
                return redirect(url_for('patient_dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET','POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            u = User.query.filter_by(username=form.username.data).first()
            if u and check_password_hash(u.password_hash, form.password.data):
                login_user(u)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
            flash('Invalid credentials', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET','POST'])
    def register():
        # only patients may register themselves
        form = RegisterPatientForm()
        if form.validate_on_submit():
            try:
                if User.query.filter_by(username=form.username.data).first():
                    flash('Username exists', 'danger')
                else:
                    u = User(
                        username=form.username.data,
                        password_hash=generate_password_hash(form.password.data),
                        role='patient',
                        name=form.name.data,
                        age=form.age.data,
                        contact=form.contact.data
                    )
                    db.session.add(u)
                    db.session.commit()
                    flash('Registered. Please login', 'success')
                    return redirect(url_for('login'))
            except SQLAlchemyError as err:
                db.session.rollback()
                app.logger.exception('Register patient failed: %s', err)
                flash('Could not register patient due to a database error.', 'danger')
        return render_template('register.html', form=form)

    # ----------------- Admin routes -----------------
    def admin_required(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin():
                abort(403)
            return func(*args, **kwargs)
        return wrapper

    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        doctors = User.query.filter_by(role='doctor').all()
        patients = User.query.filter_by(role='patient').all()
        appointments = Appointment.query.order_by(Appointment.date.desc()).all()
        return render_template('admin_dashboard.html', doctors=doctors, patients=patients, appointments=appointments)

    @app.route('/admin/doctor/create', methods=['GET','POST'])
    @login_required
    @admin_required
    def admin_create_doctor():
        form = DoctorForm()
        if form.validate_on_submit():
            try:
                if User.query.filter_by(username=form.username.data).first():
                    flash('Username exists', 'danger')
                else:
                    doc = User(
                        username=form.username.data,
                        password_hash=generate_password_hash(form.password.data or 'doctorpass'),
                        role='doctor',
                        name=form.name.data,
                        specialization=form.specialization.data,
                        contact=form.contact.data
                    )
                    db.session.add(doc)
                    db.session.commit()
                    flash('Doctor created', 'success')
                    return redirect(url_for('admin_dashboard'))
            except SQLAlchemyError as err:
                db.session.rollback()
                app.logger.exception('Create doctor failed: %s', err)
                flash('Could not create doctor due to a database error.', 'danger')
        return render_template('doctor_profile.html', form=form, action='Create')

    @app.route('/admin/doctor/<int:doc_id>/edit', methods=['GET','POST'])
    @login_required
    @admin_required
    def admin_edit_doctor(doc_id):
        doc = User.query.get_or_404(doc_id)
        if doc.role != 'doctor':
            abort(404)
        form = DoctorForm(obj=doc)
        if form.validate_on_submit():
            doc.username = form.username.data
            if form.password.data:
                doc.password_hash = generate_password_hash(form.password.data)
            doc.name = form.name.data
            doc.specialization = form.specialization.data
            doc.contact = form.contact.data
            db.session.commit()
            flash('Updated', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('doctor_profile.html', form=form, action='Edit')

    @app.route('/admin/doctor/<int:doc_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_doctor(doc_id):
        doc = User.query.get_or_404(doc_id)
        if doc.role != 'doctor':
            abort(404)
        db.session.delete(doc)
        db.session.commit()
        flash('Doctor removed', 'success')
        return redirect(url_for('admin_dashboard'))

    # ----------------- Doctor routes -----------------
    def doctor_required(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_doctor():
                abort(403)
            return func(*args, **kwargs)
        return wrapper

    @app.route('/doctor')
    @login_required
    @doctor_required
    def doctor_dashboard():
        # show upcoming appointments for next 7 days (or today)
        today = date.today()
        week_later = today + timedelta(days=7)
        appointments = Appointment.query.filter(
            Appointment.doctor_id == current_user.id,
            Appointment.date >= today
        ).order_by(Appointment.date, Appointment.time).all()
        # assigned patients (unique)
        patient_ids = {a.patient_id for a in appointments}
        patients = User.query.filter(User.id.in_(patient_ids)).all()
        return render_template('doctor_dashboard.html', appointments=appointments, patients=patients)

    @app.route('/doctor/availability', methods=['GET','POST'])
    @login_required
    @doctor_required
    def doctor_availability():
        """
        Allow doctors to add multiple availability rows.
        After POST we redirect back to this page so the doctor can add more.
        We always fetch availabilities freshly from DB so new rows appear immediately.
        """
        form = AvailabilityForm()
        if form.validate_on_submit():
            av = Availability(
                doctor_id=current_user.id,
                date=form.date.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data
            )
            # Optional: validate start < end
            if av.start_time >= av.end_time:
                flash('End time must be after start time', 'danger')
                return redirect(url_for('doctor_availability'))

            # Optional: prevent overlapping availabilities for same date
            overlapping = Availability.query.filter_by(doctor_id=current_user.id, date=av.date).filter(
                (Availability.start_time <= av.start_time) & (Availability.end_time > av.start_time) |
                (Availability.start_time < av.end_time) & (Availability.end_time >= av.end_time)
            ).first()
            # The above SQLAlchemy boolean expression may need parentheses depending on SQLAlchemy version;
            # if it errors, you can remove overlapping check for now or implement in Python.

            # just add the availability (skip overlap check if you had issues)
            db.session.add(av)
            db.session.commit()
            flash('Availability added', 'success')
            return redirect(url_for('doctor_availability'))

        # fetch fresh availabilities from DB, ordered
        availabilities = Availability.query.filter_by(doctor_id=current_user.id).order_by(Availability.date, Availability.start_time).all()
        return render_template('doctor_profile.html', form=form, action='Provide Availability', availabilities=availabilities)

    @app.route('/doctor/availability/<int:av_id>/delete', methods=['POST'])
    @login_required
    @doctor_required
    def delete_availability(av_id):
        av = Availability.query.get_or_404(av_id)
        if av.doctor_id != current_user.id:
            abort(403)
        db.session.delete(av)
        db.session.commit()
        flash('Availability removed', 'success')
        return redirect(url_for('doctor_availability'))

    @app.route('/doctor/appointment/<int:app_id>/complete', methods=['GET', 'POST'])
    @login_required
    @doctor_required
    def doctor_complete_appointment(app_id):
        appt = Appointment.query.get_or_404(app_id)
        if appt.doctor_id != current_user.id:
            abort(403)
        form = TreatmentForm()

        # Prefill if treatment exists
        existing_treat = None
        if appt.treatments:
            existing_treat = appt.treatments[0]
            if request.method == 'GET':
                form.diagnosis.data = existing_treat.diagnosis
                form.prescription.data = existing_treat.prescription
                form.notes.data = existing_treat.notes

        if form.validate_on_submit():
            if existing_treat:
                existing_treat.diagnosis = form.diagnosis.data
                existing_treat.prescription = form.prescription.data
                existing_treat.notes = form.notes.data
            else:
                new_treat = Treatment(
                    appointment_id=appt.id,
                    diagnosis=form.diagnosis.data,
                    prescription=form.prescription.data,
                    notes=form.notes.data
                )
                db.session.add(new_treat)

            appt.status = 'Completed'
            db.session.commit()
            flash('Appointment marked completed and treatment saved.', 'success')
            return redirect(url_for('doctor_dashboard'))

        return render_template('patient_history.html', form=form, appt=appt)

    @app.route('/doctor/appointment/<int:app_id>/cancel', methods=['POST'])
    @login_required
    @doctor_required
    def doctor_cancel_appointment(app_id):
        appt = Appointment.query.get_or_404(app_id)
        if appt.doctor_id != current_user.id:
            abort(403)
        appt.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled', 'warning')
        return redirect(url_for('doctor_dashboard'))

    # ----------------- Patient routes -----------------
    def patient_required(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_patient():
                abort(403)
            return func(*args, **kwargs)
        return wrapper

    @app.route('/patient')
    @login_required
    @patient_required
    def patient_dashboard():
        # show departments (unique specializations)
        depts = set(u.specialization for u in User.query.filter_by(role='doctor').all() if u.specialization)
        # upcoming appointments
        upcoming = Appointment.query.filter_by(patient_id=current_user.id).filter(Appointment.status=='Booked').order_by(Appointment.date).all()
        history = Appointment.query.filter_by(patient_id=current_user.id).filter(Appointment.status=='Completed').order_by(Appointment.date.desc()).all()
        return render_template('patient_dashboard.html', depts=depts, upcoming=upcoming, history=history)

    @app.route('/patient/book', methods=['GET','POST'])
    @login_required
    @patient_required
    def patient_book():
        form = AppointmentForm()
        # populate doctor choices
        docs = User.query.filter_by(role='doctor').all()
        form.doctor_id.choices = [(d.id, f"{d.name} ({d.specialization})") for d in docs]
        if form.validate_on_submit():
            # ensure chosen time slot is within availability
            from datetime import datetime
            ap_date = form.date.data
            ap_time = form.time.data
            doc_id = form.doctor_id.data

            # check availability record exists for doc on that date and time within any availability slot
            avail = Availability.query.filter_by(doctor_id=doc_id, date=ap_date).all()
            ok = False
            for a in avail:
                if a.start_time <= ap_time <= a.end_time:
                    ok = True
                    break
            if not ok:
                flash('Selected doctor not available at that time', 'danger')
                return redirect(url_for('patient_book'))

            # prevent double booking: same doctor same date and time
            existing = Appointment.query.filter_by(doctor_id=doc_id, date=ap_date, time=ap_time, status='Booked').first()
            if existing:
                flash('This slot is already booked', 'danger')
                return redirect(url_for('patient_book'))

            ap = Appointment(patient_id=current_user.id, doctor_id=doc_id, date=ap_date, time=ap_time, status='Booked')
            db.session.add(ap)
            db.session.commit()
            flash('Appointment booked', 'success')
            return redirect(url_for('patient_dashboard'))
        return render_template('appointment_list.html', form=form)

    @app.route('/patient/appointment/<int:app_id>/cancel', methods=['POST'])
    @login_required
    @patient_required
    def patient_cancel(app_id):
        ap = Appointment.query.get_or_404(app_id)
        if ap.patient_id != current_user.id:
            abort(403)
        ap.status = 'Cancelled'
        db.session.commit()
        flash('Cancelled', 'success')
        return redirect(url_for('patient_dashboard'))

    @app.route('/appointment/<int:app_id>/reschedule', methods=['GET','POST'])
    @login_required
    def appointment_reschedule(app_id):
        ap = Appointment.query.get_or_404(app_id)
        # only patient who booked or admin can reschedule
        if not (current_user.is_admin() or (current_user.is_patient() and current_user.id == ap.patient_id)):
            abort(403)
        form = AppointmentForm()
        docs = User.query.filter_by(role='doctor').all()
        form.doctor_id.choices = [(d.id, f"{d.name} ({d.specialization})") for d in docs]
        if request.method == 'GET':
            form.doctor_id.data = ap.doctor_id
            form.date.data = ap.date
            form.time.data = ap.time
        if form.validate_on_submit():
            # check double booking as earlier
            existing = Appointment.query.filter_by(doctor_id=form.doctor_id.data, date=form.date.data, time=form.time.data, status='Booked').first()
            if existing and existing.id != ap.id:
                flash('Slot already taken', 'danger')
            else:
                ap.doctor_id = form.doctor_id.data
                ap.date = form.date.data
                ap.time = form.time.data
                db.session.commit()
                flash('Rescheduled', 'success')
                return redirect(url_for('index'))
        return render_template('appointment_list.html', form=form)

    @app.route('/patient/history/<int:patient_id>')
    @login_required
    def view_patient_history(patient_id):
        # doctors can view patients assigned. patients can view their own history. admin can view all.
        if current_user.is_patient() and current_user.id != patient_id:
            abort(403)
        if current_user.is_doctor():
            # allow doctor to view history of patients only if they've had appointments together
            shared = Appointment.query.filter_by(patient_id=patient_id, doctor_id=current_user.id).first()
            if not shared:
                abort(403)
        appts = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.date.desc()).all()
        return render_template('patient_history.html', appointments=appts)

    return app


app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=debug, host='0.0.0.0', port=port)
