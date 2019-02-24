from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, SelectMultipleField, widgets, IntegerField, \
    DecimalField, BooleanField, FileField
from wtforms.validators import ValidationError, DataRequired, EqualTo
from app.models import User, Usergroup
from app import db


# users = []
# for u in User.query.order_by(User.usergroup_id.asc()).all():
#    users.append((str(u.id), u.name + " (" + Usergroup.query.get(u.usergroup_id).name + ")"))

class LoginForm(FlaskForm):
    username = StringField('Gebruikersnaam', validators=[DataRequired()])
    password = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Log in')


class UserRegistrationForm(FlaskForm):
    # groups = [(str(g.id), g.name) for g in Usergroup.query.all()]
    # groups = []
    # for g in Usergroup.query.all():
    #    groups.append((str(g.id), g.name))

    name = StringField('Naam', validators=[DataRequired()])
    group = SelectField('Groep')
    submit_user = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.group.choices = [(str(g.id), g.name) for g in Usergroup.query.all()]

    def updategroups(self):
        global groups
        global group
        groups = [(str(g.id), g.name) for g in Usergroup.query.all()]
        group = SelectField('Groep', choices=groups)
        # for g in Usergroup.query.all():
        #    groups.append((str(g.id), g.name))


class UserGroupRegistrationForm(FlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    submit_usergroup = SubmitField('Verstuur')


class DrinkForm(FlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    price = StringField('Prijs', validators=[DataRequired()])
    image = FileField('Afbeelding', validators=[DataRequired()])
    submit_drink = SubmitField('Verstuur')


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class UpgradeBalanceForm(FlaskForm):
    user = SelectField('Naam', validators=[DataRequired()])
    amount = StringField('Bedrag', validators=[DataRequired()])
    submit = SubmitField('Versturen')

    def __init__(self, *args, **kwargs):
        super(UpgradeBalanceForm, self).__init__(*args, **kwargs)
        users = []
        for u in User.query.order_by(User.usergroup_id.asc()).all():
            users.append((str(u.id), u.name + " (" + Usergroup.query.get(u.usergroup_id).name + ")"))
        self.user.choices = users


class ChangeDrinkForm(FlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    price = StringField('Prijs', validators=[DataRequired()])
    purchaseable = BooleanField('Beschikbaar')
    submit1 = SubmitField('Versturen')


class ChangeDrinkImageForm(FlaskForm):
    image = FileField('Afbeelding', validators=[DataRequired()])
    submit2 = SubmitField('Uploaden')
