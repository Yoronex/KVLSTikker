from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, SelectMultipleField, widgets, FormField, FieldList, Form
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

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class DrinkRegistrationForm(FlaskForm):
    nestedDict = {}
    for g in Usergroup.query.all():
        dict = {}
        for u in g.users.all():
            dict[u.id] = BooleanField(label=u.name)
        nestedDict[g.id] = dict

    nestedDict2 = {}
    nestedDict2[0] = BooleanField(label="Ja/Nee")

    list = [MultiCheckboxField("Groep", choices=groups)]

    example = MultiCheckboxField("Groep", choices=groups)

    submit = SubmitField('Verstuur')

class IMForm(FlaskForm):
    protocol = SelectField(choices=[('aim', 'AIM'), ('msn', 'MSN')])
    username = StringField()

class ContactForm(FlaskForm):
    first_name  = StringField()
    last_name   = StringField()
    im_accounts = FieldList(FormField(IMForm))