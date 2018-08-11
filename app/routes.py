from flask import render_template, flash, redirect, url_for
from app import app, db
from app.forms import LoginForm, UserRegistrationForm, DrinkRegistrationForm, ContactForm, UpgradeBalanceForm
from app.models import User, Usergroup, Product, Purchase, Upgrade

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home', Product=Product)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}'.format(form.username.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = UserRegistrationForm()
    if form.validate_on_submit():
        #print("User wants to register!")
        user = User(name=form.name.data, usergroup_id=form.group.data)
        #print(user.name, user.usergroup_id)
        db.session.add(user)
        db.session.commit()
        flash("Gebruiker {} succesvol geregistreerd".format(user.name))
        return redirect(url_for('index'))
    return render_template('register.html', title='Registreren', form=form)

@app.route('/upgrade', methods=['GET', 'POST'])
def upgrade():
    form = UpgradeBalanceForm()
    if form.validate_on_submit():
        upgrade = Upgrade(user_id=form.user.data, amount=form.amount.data)
        user = User.query.get(upgrade.user_id)
        db.session.add(upgrade)
        user.balance = user.balance + form.amount.data
        db.session.commit()
        flash("Gebruiker {} heeft succesvol opgewaardeerd met {} euro".format(user.name, upgrade.amount))
        return redirect(url_for('index'))
    return render_template('upgrade.html', title='Opwaarderen', form=form)

@app.route('/balance')
def balance():
    return render_template('balance.html', title='Saldo', Usergroup=Usergroup)

@app.route('/users')
def users():
    return render_template('users.html', title='Gebruikers', User=User)

@app.route('/purchasehistory')
def purchasehistory():
    return render_template('purchasehistory.html', title='Aankoophistorie', User=User, Product=Product, Purchase=Purchase)

@app.route('/drink/<int:drinkid>', methods=['GET', 'POST'])
def drink(drinkid):
    drink = Product.query.get(drinkid)
    return render_template('drink.html', title=drink.name, drink=drink, User=User, Usergroup=Usergroup)

@app.route('/drink/<int:drinkid>/<int:userid>')
def purchase(drinkid, userid):
    drink = Product.query.get(drinkid)
    user = User.query.get(userid)
    purchase = Purchase(user_id=user.id, product_id=drink.id, price=drink.price)
    db.session.add(purchase)
    user.balance = user.balance - drink.price
    db.session.commit()
    flash("{} voor {} verwerkt".format(drink.name, user.name))
    return redirect(url_for('drink', drinkid=drinkid))

@app.route('/testforms')
def test():
    form = ContactForm()
    return render_template('testforms.html', form=form)