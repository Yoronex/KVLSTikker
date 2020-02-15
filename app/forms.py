import os

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, SelectMultipleField, widgets, IntegerField, DecimalField, BooleanField, FileField, TextAreaField, PasswordField
from wtforms.fields.html5 import DateField
from wtforms.validators import ValidationError, DataRequired, EqualTo, Email
from app.models import User, Usergroup, Product
from sqlalchemy import and_
from app import db, app


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
    email = StringField('Email', validators=[DataRequired(), Email()])
    group = SelectField('Groep')
    profitgroup = SelectField('Opbrengst gaat naar')
    birthday = DateField('Verjaardag', validators=[DataRequired()])
    submit_user = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        choices = [(str(g.id), g.name) for g in Usergroup.query.all()]
        self.group.choices = choices
        self.profitgroup.choices = choices

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
    category = SelectField('Categorie', choices=[("", ""), ("Bieren", "Bieren"), ("Mixjes", "Mixjes"), ("Shots", "Shots")])
    pos = SelectField('Positie', validators=[DataRequired()])
    image = FileField('Afbeelding (statisch)', validators=[DataRequired()])
    hoverimage = FileField('Afbeelding (hover)')
    recipe = StringField('Recept')
    inventory_warning = IntegerField('Inventaris waarschuwing', default=0)
    alcohol = StringField('Alcoholpercentage (in %)')
    volume = StringField('Hoeveelheid (in milliliters)')
    unit = StringField('Hoeveelheid (e.g. 1 flesje, 1 shotje, etc)')
    submit_drink = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(DrinkForm, self).__init__(*args, **kwargs)
        positions = []
        count = -1
        for p in Product.query.order_by(Product.order.asc()).all():
            count = count + 1
            suffix = ""
            if not p.purchaseable:
                suffix = " (UIT)"
            positions.append((str(count), str(p.order) + ". " + p.name + suffix))
        positions.append((str(count), "Achteraan"))
        self.pos.choices = positions
        self.pos.default = len(positions) - 1


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class UpgradeBalanceForm(FlaskForm):
    user = SelectField('Naam', validators=[DataRequired()])
    description = SelectField('Beschrijving', validators=[DataRequired()], choices=[("Opwaardering", "Opwaardering"), ("Vergoeding inkoop", "Vergoeding inkoop"), ("Vergoeding diner", "Vergoeding diner")])
    amount = StringField('Bedrag (in Tikker)', validators=[DataRequired()])
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
    category = SelectField('Categorie', choices=[("", ""), ("Bieren", "Bieren"), ("Mixjes", "Mixjes"), ("Shots", "Shots")])
    pos = SelectField('Positie', validators=[DataRequired()])
    purchaseable = BooleanField('Beschikbaar', default=True)
    recipe = StringField('Recept')
    inventory_warning = IntegerField('Inventaris waarschuwing')
    alcohol = StringField('Alcoholpercentage (in %)', default=0)
    volume = StringField('Hoeveelheid (in milliliters)', default=0)
    unit = StringField('Hoeveelheid (e.g. 1 flesje, 1 shotje, etc)')
    submit1 = SubmitField('Versturen')

    def __init__(self, *args, **kwargs):
        super(ChangeDrinkForm, self).__init__(*args, **kwargs)
        positions = []
        count = -1
        for p in Product.query.order_by(Product.order.asc()).all():
            count = count + 1
            suffix = ""
            if not p.purchaseable:
                suffix = " (UIT)"
            positions.append((str(count), str(p.order) + ". " + p.name + suffix))
        positions.append((str(count + 1), "Achteraan"))
        self.pos.choices = positions
        self.pos.default = len(positions) - 1


class ChangeDrinkImageForm(FlaskForm):
    image = FileField('Afbeelding (statisch)')
    hoverimage = FileField('Afbeelding (hover)')
    submit2 = SubmitField('Uploaden')


class AddInventoryForm(FlaskForm):
    product = SelectField('Product', validators=[DataRequired()])
    quantity = StringField('Aantal', validators=[DataRequired()])
    purchase_price = StringField('Inkoopprijs per stuk', validators=[DataRequired()])
    note = TextAreaField('Notities')
    submit_inventory = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(AddInventoryForm, self).__init__(*args, **kwargs)
        products = []
        for p in Product.query.filter(and_(Product.recipe_input == None), (Product.purchaseable == True)).all():
            products.append((str(p.id), p.name))
        self.product.choices = products


class PayOutProfitForm(FlaskForm):
    usergroup = SelectField('Groep', validators=[DataRequired()])
    amount = StringField('Bedrag', validators=[DataRequired()])
    verification = PasswordField('Verificatiecode', validators=[DataRequired()])
    submit_payout = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(PayOutProfitForm, self).__init__(*args, **kwargs)
        usergroups = []
        for u in Usergroup.query.all():
            usergroups.append((str(u.id), u.name))
        self.usergroup.choices = usergroups


class AddQuoteForm(FlaskForm):
    quote = TextAreaField('Quote', validators=[DataRequired()])
    submit_quote = SubmitField('Verstuur')


class SlideInterruptForm(FlaskForm):
    interrupt = TextAreaField('Bericht', validators=[DataRequired()])
    submit_interrupt = SubmitField('Verstuur')


class ChooseSpotifyUser(FlaskForm):
    spotify_user = SelectField('Account')
    spotify_user_name = StringField('Naam voor nieuwe gebruiker')
    spotify_submit = SubmitField('Log in')

    def __init__(self, *args, **kwargs):
        super(ChooseSpotifyUser, self).__init__(*args, **kwargs)
        names = [("0", "Nieuw account toevoegen")]
        for n in os.listdir(app.config['SPOTIFY_CACHE_FOLDER']):
            names.append((n[19:], n[19:]))
        self.spotify_user.choices = names


class RoundForm(FlaskForm):
    round_giver = SelectField("")

    def __init__(self, *args, **kwargs):
        super(RoundForm, self).__init__(*args, **kwargs)
        users = [("0", "")]
        for group in Usergroup.query.all():
            for u in group.users:
                users.append((str(u.id), "{} ({})".format(u.name, group.name)))
        self.round_giver.choices = users
