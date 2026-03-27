from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField, DateField, TimeField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterPatientForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    name = StringField('Full name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[Optional()])
    contact = StringField('Contact', validators=[Optional()])
    submit = SubmitField('Register')

class DoctorForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Optional()])
    name = StringField('Full name', validators=[DataRequired()])
    specialization = StringField('Specialization', validators=[DataRequired()])
    contact = StringField('Contact', validators=[Optional()])
    submit = SubmitField('Create / Update')

class AvailabilityForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    submit = SubmitField('Provide Availability')

class AppointmentForm(FlaskForm):
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    time = TimeField('Time', validators=[DataRequired()])
    submit = SubmitField('Book Appointment')

class TreatmentForm(FlaskForm):
    diagnosis = TextAreaField('Diagnosis', validators=[Optional()])
    prescription = TextAreaField('Prescription', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')
