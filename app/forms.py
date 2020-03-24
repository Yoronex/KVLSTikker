import os

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, SelectMultipleField, IntegerField, BooleanField, FileField, TextAreaField, PasswordField
from wtforms.fields.html5 import DateField, DecimalField
from wtforms.validators import DataRequired, Email
from app.models import User, Usergroup, Product
from sqlalchemy import and_
from app import app


class FlexibleDecimalField(DecimalField):
    def process_formdata(self, valuelist):
        if valuelist:
            valuelist[0] = valuelist[0].replace(",", ".")
        return super(FlexibleDecimalField, self).process_formdata(valuelist)


class ExtendedFlaskForm(FlaskForm):
    def get_fields(self):
        return list(self.data.keys())[:-1]


class UserRegistrationForm(ExtendedFlaskForm):
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


class UserGroupRegistrationForm(ExtendedFlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    submit_usergroup = SubmitField('Verstuur')


class DrinkForm(ExtendedFlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    price = FlexibleDecimalField('Prijs', validators=[DataRequired()], places=2)
    category = SelectField('Categorie', choices=[("", ""), ("Bieren", "Bieren"), ("Mixjes", "Mixjes"), ("Shots", "Shots")])
    pos = SelectField('Positie', validators=[DataRequired()])
    image = FileField('Afbeelding (statisch)', validators=[DataRequired()])
    hoverimage = FileField('Afbeelding (hover)')
    recipe = StringField('Recept')
    inventory_warning = IntegerField('Inventaris waarschuwing', default=0)
    alcohol = FlexibleDecimalField('Alcoholpercentage (in %)', places=2)
    volume = FlexibleDecimalField('Hoeveelheid (in milliliters)')
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


class UpgradeBalanceForm(ExtendedFlaskForm):
    user = SelectField('Naam', validators=[DataRequired()])
    amount = FlexibleDecimalField('Bedrag (in Tikker)', validators=[DataRequired()], places=2)
    upgr_submit = SubmitField('Versturen')

    def __init__(self, *args, **kwargs):
        super(UpgradeBalanceForm, self).__init__(*args, **kwargs)
        users = []
        for u in User.query.order_by(User.usergroup_id.asc()).all():
            users.append((str(u.id), u.name + " (" + Usergroup.query.get(u.usergroup_id).name + ")"))
        self.user.choices = users


class DeclarationForm(ExtendedFlaskForm):
    user = SelectField('Naam', validators=[DataRequired()])
    amount = FlexibleDecimalField('Bedrag', validators=[DataRequired()])
    description = SelectField('Beschrijving', validators=[DataRequired()], choices=[("Vergoeding inkoop", "Vergoeding inkoop"), ("Vergoeding diner", "Vergoeding diner"), ("Vergoeding opkomst", "Vergoeding opkomst")])
    payer = SelectField('Wie vergoedt?', validators=[DataRequired()])
    decl_submit = SubmitField('Versturen')

    def __init__(self, *args, **kwargs):
        super(DeclarationForm, self).__init__(*args, **kwargs)
        users = []
        groups = [("0", "de Bar")]
        for u in User.query.order_by(User.usergroup_id.asc()).all():
            users.append((str(u.id), u.name + " (" + Usergroup.query.get(u.usergroup_id).name + ")"))
        for g in Usergroup.query.all():
            groups.append((str(g.id), g.name))
        self.user.choices = users
        self.payer.choices = groups


class ChangeDrinkForm(ExtendedFlaskForm):
    name = StringField('Naam', validators=[DataRequired()])
    price = FlexibleDecimalField('Prijs', validators=[DataRequired()])
    category = SelectField('Categorie', choices=[("", ""), ("Bieren", "Bieren"), ("Mixjes", "Mixjes"), ("Shots", "Shots")])
    pos = SelectField('Positie', validators=[DataRequired()])
    purchaseable = BooleanField('Beschikbaar', default=True)
    recipe = StringField('Recept')
    inventory_warning = IntegerField('Inventaris waarschuwing')
    alcohol = FlexibleDecimalField('Alcoholpercentage (in %)', default=0)
    volume = FlexibleDecimalField('Hoeveelheid (in milliliters)', default=0)
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


class ChangeDrinkImageForm(ExtendedFlaskForm):
    image = FileField('Afbeelding (statisch)')
    hoverimage = FileField('Afbeelding (hover)')
    submit2 = SubmitField('Uploaden')


class AddInventoryForm(ExtendedFlaskForm):
    product = SelectField('Product', validators=[DataRequired()])
    quantity = IntegerField('Aantal', validators=[DataRequired()])
    purchase_price = FlexibleDecimalField('Inkoopprijs per stuk', validators=[DataRequired()])
    note = TextAreaField('Notities')
    submit_inventory = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(AddInventoryForm, self).__init__(*args, **kwargs)
        products = []
        for p in Product.query.filter(and_(Product.recipe_input == None), (Product.purchaseable == True)).all():
            products.append((str(p.id), p.name))
        self.product.choices = products


class PayOutProfitForm(ExtendedFlaskForm):
    usergroup = SelectField('Groep', validators=[DataRequired()])
    amount = FlexibleDecimalField('Bedrag', validators=[DataRequired()])
    verification = PasswordField('Verificatiecode', validators=[DataRequired()])
    submit_payout = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(PayOutProfitForm, self).__init__(*args, **kwargs)
        usergroups = []
        for u in Usergroup.query.all():
            usergroups.append((str(u.id), u.name))
        self.usergroup.choices = usergroups


class AddQuoteForm(ExtendedFlaskForm):
    quote = TextAreaField('Quote', validators=[DataRequired()])
    author = SelectField('Wie ben je?', validators=[DataRequired()])
    submit_quote = SubmitField('Verstuur')

    def __init__(self, *args, **kwargs):
        super(AddQuoteForm, self).__init__(*args, **kwargs)
        users = []
        for u in User.query.order_by(User.usergroup_id.asc()).all():
            users.append((str(u.name), u.name + " (" + Usergroup.query.get(u.usergroup_id).name + ")"))
        self.author.choices = users


class SlideInterruptForm(ExtendedFlaskForm):
    interrupt = TextAreaField('Bericht', validators=[DataRequired()])
    submit_interrupt = SubmitField('Verstuur')


class ChooseSpotifyUser(ExtendedFlaskForm):
    spotify_user = SelectField('Account')
    spotify_user_name = StringField('Naam voor nieuwe gebruiker')
    spotify_submit = SubmitField('Log in')

    def __init__(self, *args, **kwargs):
        super(ChooseSpotifyUser, self).__init__(*args, **kwargs)
        names = [("0", "Nieuw account toevoegen")]
        for n in os.listdir(app.config['SPOTIFY_CACHE_FOLDER']):
            names.append((n[19:], n[19:]))
        self.spotify_user.choices = names


class RoundForm(ExtendedFlaskForm):
    round_giver = SelectField("")

    def __init__(self, *args, **kwargs):
        super(RoundForm, self).__init__(*args, **kwargs)
        users = [("0", "")]
        for group in Usergroup.query.all():
            for u in group.users:
                users.append((str(u.id), "{} ({})".format(u.name, group.name)))
        self.round_giver.choices = users


class BorrelModeForm(ExtendedFlaskForm):
    products = SelectMultipleField("Producten")
    user = SelectField("Wie trakteert?")
    amount = IntegerField("Hoeveel")
    submit = SubmitField("Versturen")

    def __init__(self, *args, **kwargs):
        super(BorrelModeForm, self).__init__(*args, **kwargs)
        product_list = []
        for p in Product.query.all():
            product_list.append((str(p.id), "{} (€ {})".format(p.name, '%.2f' % p.price)))
        self.products.choices = product_list

        users = []
        for group in Usergroup.query.all():
            for u in group.users:
                users.append((str(u.id), "{} ({})".format(u.name, group.name)))
        self.user.choices = users


class SoundBoardForm(ExtendedFlaskForm):
    name = StringField("Naam", validators=[DataRequired()])
    key = StringField("Toetsenbord toets")
    code = IntegerField("Javascript Toetscode")
    file = FileField("Audiobestand", validators=[DataRequired()])
    submit = SubmitField("Versturen")


class TransactionFilterForm(ExtendedFlaskForm):
    f_transaction_type = SelectField("Transactiesoort", choices=(('all', 'Alle'), ('upgr', 'Opwaarderingen'), ('pur', 'Aankopen')))
    f_transaction_user = SelectField("Gebruiker")
    f_transaction_product = SelectField("Product")
    f_transaction_round = SelectField("Rondje", choices=(('all', 'Alle'), ('1', 'Ja'), ('0', 'Nee')))

    def __init__(self, *args, **kwargs):
        super(TransactionFilterForm, self).__init__(*args, **kwargs)
        product_list = [('0', "Alle")]
        for p in Product.query.all():
            product_list.append((str(p.id), p.name))
        self.f_transaction_product.choices = product_list

        users = [('0', 'Iedereen')]
        for group in Usergroup.query.all():
            for u in group.users:
                users.append((str(u.id), "{} ({})".format(u.name, group.name)))
        self.f_transaction_user.choices = users


class UserTransactionFilterForm(ExtendedFlaskForm):
    f_transaction_type = SelectField("Transactiesoort", choices=(('all', 'Alle'), ('upgr', 'Opwaarderingen'), ('pur', 'Aankopen')))
    f_transaction_product = SelectField("Product")
    f_transaction_round = SelectField("Rondje", choices=(('all', 'Alle'), ('1', 'Ja'), ('0', 'Nee')))

    def __init__(self, *args, **kwargs):
        super(UserTransactionFilterForm, self).__init__(*args, **kwargs)
        product_list = [('0', "Alle")]
        for p in Product.query.all():
            product_list.append((str(p.id), p.name))
        self.f_transaction_product.choices = product_list


class UsersFilterForm(ExtendedFlaskForm):
    f_user_usergroup = SelectField("Groep")
    f_user_profitgroup = SelectField("Winstgroep")

    def __init__(self, *args, **kwargs):
        super(UsersFilterForm, self).__init__(*args, **kwargs)
        group_list = [('0', 'Alle')]
        for g in Usergroup.query.all():
            group_list.append((str(g.id), g.name))
        self.f_user_usergroup.choices = group_list
        self.f_user_profitgroup.choices = group_list


class ProductFilterForm(ExtendedFlaskForm):
    f_product_category = SelectField("Categorie", choices=(('all', 'Alle'), ('Bieren', 'Bieren'), ('Shots', 'Shots'),
                                                           ('Mixjes', 'Mixjes')))
    f_product_purchaseable = SelectField("Beschikbaar", choices=(('all', 'Alle'), ('1', 'Ja'), ('0', 'Nee')))
