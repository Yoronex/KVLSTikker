from typing import Dict, Any

from threading import Thread
from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm, ChangeDrinkForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math

def view_user_dlc(*args, **kwargs):
    user_id = request.view_args['userid']
    user = User.query.get(user_id)
    return [{'text': user.name, 'url': url_for('user', userid=user_id)}]

def view_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('drink', drinkid=drink_id)}]

def query_to_dataframe(query, columns):
    nestedDict = {}
    for q in query:
        nestedDict[q.id] = q.__dict__
    return pd.DataFrame.from_dict(nestedDict, orient="index", columns=columns)

def make_autopct(values):
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct*total/100.0))
        return '{p:.2f}%  ({v:d})'.format(p=pct,v=val)
    return my_autopct

plotcolours = ["#0b8337", "#ffd94a", "#707070"]

@app.route('/')
@app.route('/index')
@app.route('/drink')
@register_breadcrumb(app, '.', 'Home', order=0)
@register_breadcrumb(app, '.drink', 'Product', order=1)
def index():
    return render_template('index.html', title='Home', Product=Product)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}'.format(form.username.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/upgrade', methods=['GET', 'POST'])
@register_breadcrumb(app, '.upgrade', 'Opwaarderen', order=1)
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
@register_breadcrumb(app, '.balance', "Saldo's", order=1)
def balance():
    usergroups = Usergroup.query.all()
    return render_template('balance.html', title='Saldo', usergroups=usergroups, amount_usergroups=len(usergroups))

@app.route('/user')
@register_breadcrumb(app, '.user', 'Gebruiker', order=1)
def users():
    return redirect(url_for('balance'))

@app.route('/user/<int:userid>')
@register_breadcrumb(app, '.user.id', '', dynamic_list_constructor=view_user_dlc, order=2)
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
@register_breadcrumb(app, '.drink.id', '', dynamic_list_constructor=view_drink_dlc, order=2)
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

##
#
# Admin Panel
#
##

@app.route('/admin', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin', 'Beheerderspaneel', order=1)
def admin():
    return render_template('admin.html', title='Admin paneel')

@app.route('/admin/users', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.users', 'Gebruikersbeheer', order=2)
def admin_users():
    form = UserRegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, usergroup_id=form.group.data)
        db.session.add(user)
        db.session.commit()
        flash("Gebruiker {} succesvol geregistreerd".format(user.name))
        return redirect(url_for('admin_users'))
    return render_template("manusers.html", title="Gebruikersbeheer", backurl=url_for('index'), User=User, Usergroup=Usergroup, form=form)

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
@register_breadcrumb(app, '.admin.transactions', 'Transactiebeheer', order=2)
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

@app.route('/admin/drinks', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks', 'Productbeheer', order=2)
def admin_drinks():
    drinks = Product.query.all()
    form = DrinkForm()
    if form.validate_on_submit():
        product = Product(name=form.name.data, price=form.price.data, purchaseable=True)
        db.session.add(product)
        db.session.commit()
        flash("Product {} succesvol aangemaakt".format(product.name))
        return redirect(url_for('admin_drinks'))
    return render_template('mandrinks.html', drinks=drinks, form=form)

@app.route('/admin/drinks/edit/<int:drinkid>', methods=['GET', 'POST'])
def admin_drinks_edit(drinkid):
    product = Product.query.get(drinkid)
    form = ChangeDrinkForm()
    if form.validate_on_submit():
        product.name = form.name.data
        product.price = form.price.data
        product.purchaseable = form.purchaseable.data
        db.session.commit()
        flash("Product {} (ID: {}) succesvol aangepast!".format(product.name, product.id))
        return redirect(url_for('admin_drinks'))
    return render_template('editdrink.html', product=product, form=form)

@app.route('/admin/drinks/delete/<int:drinkid>')
def admin_drinks_delete(drinkid):
    product = Product.query.get(drinkid)
    product.purchaseable = False
    db.session.commit()
    flash('Product {} is niet meer beschikbaar'.format(product.name))
    return redirect(url_for('admin_drinks'))

@app.route('/admin/usergroups', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.usergroups', 'Groepenbeheer', order=2)
def admin_usergroups():
    form = UserGroupRegistrationForm()
    if form.validate_on_submit():
        usergroup = Usergroup(name=form.name.data)
        db.session.add(usergroup)
        db.session.commit()
        flash("Groep {} succesvol aangemaakt".format(usergroup.name))
        return redirect(url_for('admin_usergroups'))
    return render_template("manusergroups.html", title="Groepen", form=form, Usergroup=Usergroup)

@app.route('/admin/usergroups/delete/<int:usergroupid>')
def admin_usergroups_delete(usergroupid):
    usergroup = Usergroup.query.get(usergroupid)
    users = usergroup.users.all()
    if len(users) == 0:
        message = "groep " + usergroup.name + " wilt verwijderen?"
        agree_url = url_for("admin_usergroups_delete_exec", usergroupid=usergroupid)
        return_url = url_for("admin_usergroups")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url, return_url=return_url)
    else:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.")
        return redirect(url_for('admin_usergroups'))

@app.route('/admin/usergroups/delete/<int:usergroupid>/exec')
def admin_usergroups_delete_exec(usergroupid):
    usergroup = Usergroup.query.get(usergroupid)
    db.session.delete(usergroup)
    db.session.commit()
    flash("Groep {} verwijderd".format(usergroup.name))
    return redirect(url_for('admin_usergroups'))

##
#
# Statistieken
#
##

@app.route('/stats')
def stats():
    return None

@app.route('/stats/user/<int:userid>')
def stats_user(userid):
    user = User.query.get(userid)
    df = query_to_dataframe(user.purchases.all(), ["product_id", "amount", "price"])
    filenames = []

    def count_plot(df):
        products = []
        for p in Product.query.all():
            products.append(p.id)

        countDrinks = dict.fromkeys(products)
        for d in countDrinks:
            countDrinks[d] = 0

        for index, row in df.iterrows():
            countDrinks[int(row["product_id"])] = countDrinks[int(row["product_id"])] + row["amount"]

        return countDrinks

    def barplot(df):
        D = count_plot(df)

        fig1 = plt.figure()
        ax1 = plt.gca()
        bars = ax1.bar(range(len(D)), list(D.values()), align='center', color=plotcolours)
        ax1.set_xticks(range(len(D.values())))
        #ax.set_xticklabels(("A", "B"))
        ax1.set_xticklabels([Product.query.get(x).name for x in D.keys()])
        yint = range(int(min(D.values())), int(max(D.values())+1))
        ax1.set_yticks(yint)
        ax1.set_title("Aantal bestelde producten")
        fig1.savefig('app/static/graphs/plot-bar-user-{}.png'.format(userid), transparent=True)

    def piechart(df):
        D = count_plot(df)

        fig = plt.figure()
        ax = plt.gca()
        pies = ax.pie(list(D.values()), colors=plotcolours, explode=[0.02]*len(D.values()), labels=[Product.query.get(x).name for x in D.keys()], autopct=make_autopct(list(D.values())))
        ax.set_title("Aantal bestelde producten")
        fig.savefig('app/static/graphs/plot-pie-user-{}.png'.format(userid), transparent=True)

    def linechart(df)
    thread1 = Thread(target=barplot, args=(df, ))
    thread2 = Thread(target=piechart, args=(df, ))
    thread1.start()
    thread2.start()
    thread1.join()
    #barplot(df)
    filenames.append("graphs/plot-bar-user-{}.png".format(userid))
    thread2.join()
    #piechart(df)
    filenames.append("graphs/plot-pie-user-{}.png".format(userid))

    return render_template('statsuser.html', title="Statistieken voor {}".format(user.name), user=user, filenames=filenames)

@app.route('/stats/drink/<int:drinkid>')
def stats_drink(drinkid):
    return None