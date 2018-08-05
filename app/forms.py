from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import ValidationError, DataRequired, EqualTo
from app.models import User, Usergroup
from app import db

groups = [(str(g.id), g.name) for g in Usergroup.query.all()]

class LoginForm(FlaskForm):
    username = StringField('Gebruikersnaam', validators=[DataRequired()])
    password = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Log in')

class UserRegistrationForm(FlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    group = SelectField('Groep', choices=groups)
    submit = SubmitField('Registreer')
