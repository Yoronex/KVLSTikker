from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, SelectMultipleField, widgets, FormField, FieldList, Form, IntegerField
from wtforms.validators import ValidationError, DataRequired, EqualTo
from app.models import User, Usergroup
from app import db

users = []
for u in User.query.order_by(User.usergroup_id.asc()).all():
    users.append((str(u.id), u.name + " (" + Usergroup.query.get(u.usergroup_id).name + ")"))

class LoginForm(FlaskForm):
    username = StringField('Gebruikersnaam', validators=[DataRequired()])
    password = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Log in')

class UserRegistrationForm(FlaskForm):
    groups = [(str(g.id), g.name) for g in Usergroup.query.all()]

    name = StringField('Naam', validators=[DataRequired()])
    group = SelectField('Groep', choices=groups)
    submit = SubmitField('Registreer')

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class UpgradeBalanceForm(FlaskForm):
    user = SelectField('Naam', choices=users, validators=[DataRequired()])
    amount = IntegerField('Bedrag', validators=[DataRequired()])
    submit = SubmitField('Versturen')

class DrinkRegistrationForm(FlaskForm):
    nestedDict = {}
    for g in Usergroup.query.all():
        dict = {}
        for u in g.users.all():
            dict[u.id] = BooleanField(label=u.name)
        nestedDict[g.id] = dict

    nestedDict2 = {}
    nestedDict2[0] = BooleanField(label="Ja/Nee")

    submit = SubmitField('Verstuur')

class IMForm(FlaskForm):
    protocol = SelectField(choices=[('aim', 'AIM'), ('msn', 'MSN')])
    username = StringField()

class ContactForm(FlaskForm):
    first_name  = StringField()
    last_name   = StringField()
    im_accounts = FieldList(FormField(IMForm))