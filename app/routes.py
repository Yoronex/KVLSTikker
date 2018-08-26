from flask import render_template, flash, redirect, url_for
from app import app, db
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction

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
        db.session.add(upgrade)
        db.session.commit()
        user = User.query.get(upgrade.user_id)
        user.balance = user.balance + float(form.amount.data)
        transaction = Transaction(user_id=form.user.data, upgrade_id=upgrade.id, balchange=upgrade.amount, newbal=user.balance)
        db.session.add(transaction)
        db.session.commit()
        flash("Gebruiker {} heeft succesvol opgewaardeerd met {} euro".format(user.name, upgrade.amount))
        return redirect(url_for('index'))
    return render_template('upgrade.html', title='Opwaarderen', form=form)

@app.route('/balance')
def balance():
    usergroups = Usergroup.query.all()
    return render_template('balance.html', title='Saldo', usergroups=usergroups, amount_usergroups=len(usergroups))

@app.route('/users')
def users():
    return render_template('users.html', title='Gebruikers', User=User)

@app.route('/user/<int:userid>')
def user(userid):
    user = User.query.get(userid)
    transactions = user.transactions.order_by(Transaction.id.desc()).all()
    purchases = user.purchases.all()
    upgrades = user.upgrades.all()
    return render_template('user.html', user=user, transactions=transactions, Purchase=Purchase, upgrades=upgrades, Product=Product)

@app.route('/purchasehistory')
def purchasehistory():
    return render_template('purchasehistory.html', title='Aankoophistorie', User=User, Product=Product, Purchase=Purchase)

@app.route('/drink/<int:drinkid>', methods=['GET', 'POST'])
def drink(drinkid):
    drink = Product.query.get(drinkid)
    usergroups = Usergroup.query.all()
    return render_template('drink.html', title=drink.name, drink=drink, User=User, usergroups=usergroups, amount_usergroups=len(usergroups))

@app.route('/drink/<int:drinkid>/<int:userid>')
def purchase(drinkid, userid):
    drink = Product.query.get(drinkid)
    user = User.query.get(userid)
    amount = 1
    user.balance = user.balance - float(drink.price) * amount
    purchase = Purchase(user_id=user.id, product_id=drink.id, price=drink.price, amount=amount)
    db.session.add(purchase)
    db.session.commit()
    balchange = -drink.price*amount
    transaction = Transaction(user_id=user.id, purchase_id=purchase.id, balchange=balchange, newbal=user.balance)
    db.session.add(transaction)
    db.session.commit()
    flash("{} voor {} verwerkt".format(drink.name, user.name))
    return redirect(url_for('drink', drinkid=drinkid))

@app.route('/testforms', methods=['GET', 'POST'])
def test():
    form = DrinkForm()
    if form.validate_on_submit():
        product = Product(name=form.name.data, price=form.price.data, purchaseable=True)
        db.session.add(product)
        db.session.commit()
        flash("Product {} succesvol aangemaakt".format(product.name))
        return redirect(url_for('admin'))
    return render_template('testforms.html', form=form)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    form1 = UserGroupRegistrationForm()
    name1 = "Groep aanmaken"
    form2 = UserRegistrationForm()
    name2 = "Gebruiker aanmaken"
    form3 = DrinkForm()
    name3 = "Product aanmaken"
    if form1.submit_usergroup.data and form1.validate_on_submit():
        usergroup = Usergroup(name=form1.name.data)
        db.session.add(usergroup)
        db.session.commit()
        flash("Groep {} succesvol aangemaakt".format(usergroup.name))
        #form2.updategroups()
        return redirect(url_for('admin'))
    if form2.submit_user.data and form2.validate_on_submit():
        user = User(name=form2.name.data, usergroup_id=form2.group.data)
        db.session.add(user)
        db.session.commit()
        flash("Gebruiker {} succesvol geregistreerd".format(user.name))
        return redirect(url_for('admin'))
    if form3.submit_drink.data and form3.validate_on_submit():
        product = Product(name=form3.name.data, price=form3.price.data, purchaseable=True)
        db.session.add(product)
        db.session.commit()
        flash("Product {} succesvol aangemaakt".format(product.name))
        return redirect(url_for('admin'))
    return render_template('admin.html', title='Admin paneel', form1=form1, form2=form2, form3=form3, name1=name1, name2=name2, name3=name3)

@app.route('/admin/users')
def admin_users():
    return render_template("manusers.html", title="Gebruikers", User=User, Usergroup=Usergroup)

@app.route('/admin/users/delete/<int:userid>')
def admin_users_delete(userid):
    user = User.query.get(userid)
    if user.balance == 0.0:
        message = "gebruiker " + user.name + " wilt verwijderen? Alle historie gaat hierbij verloren!"
        agree_url = url_for("admin_users_delete_exec", userid=userid)
        return_url = url_for("admin_users")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url, return_url=return_url)
    else:
        flash("Deze gebruiker heeft nog geen saldo van € 0!")
        return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:userid>/exec')
def admin_users_delete_exec(userid):
    user = User.query.get(userid)
    for t in user.transactions.all():
        db.session.delete(t)
    for u in user.upgrades.all():
        db.session.delete(u)
    for p in user.purchases.all():
        db.session.delete(p)
    db.session.delete(user)
    db.session.commit()
    flash("Gebruiker {} verwijderd".format(user.name))
    return redirect(url_for('admin_users'))

@app.route('/admin/transactions')
def admin_transactions():
    transactions = Transaction.query.all()
    return render_template('mantransactions.html', User=User, transactions=transactions, Purchase=Purchase, Product=Product)

@app.route('/admin/transactions/delete/<int:tranid>')
def admin_transactions_delete(tranid):
    transaction = Transaction.query.get(tranid)
    message = "transactie met ID " + str(transaction.id) + " wilt verwijderen?"
    agree_url = url_for("admin_transactions_delete_exec", tranid=tranid)
    return_url = url_for("admin_transactions")
    return render_template("verify.html", title="Bevestigen", message=message, transaction=transaction, agree_url=agree_url, return_url=return_url)

@app.route('/admin/transactions/delete/<int:tranid>/exec')
def admin_transactions_delete_exec(tranid):
    transaction = Transaction.query.get(tranid)
    if transaction.purchase_id is None:
        upgrade = Upgrade.query.get(transaction.upgrade_id)
        db.session.delete(upgrade)
    else:
        purchase = Purchase.query.get(transaction.purchase_id)
        db.session.delete(purchase)
    for t in Transaction.query.filter(Transaction.user_id == transaction.user_id, Transaction.timestamp > transaction.timestamp).all():
        t.newbal = t.newbal - transaction.balchange
    user = User.query.get(transaction.user_id)
    user.balance = user.balance - transaction.balchange
    db.session.delete(transaction)
    db.session.commit()
    flash("Transactie met ID {} succesvol verwijderd!".format(transaction.id))
    return redirect(url_for('admin_transactions'))
