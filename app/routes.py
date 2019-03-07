from typing import Dict, Any

from threading import Thread
from flask import render_template, flash, redirect, url_for, request
from app import app
from app.dbhandler import dbhandler
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm, ChangeDrinkForm, ChangeDrinkImageForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math
from datetime import datetime
from dateutil import tz

db_handler = dbhandler()

def is_filled(data):
   if data == None:
      return False
   if data == '':
      return False
   if data == []:
      return False
   return True

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.Config["ALLOWED_EXTENSIONS"]

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

def convert_to_local_time(transactions):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    result = []

    for t in transactions:
    # utc = datetime.utcnow()
        utc = datetime.strptime(t.datetime, '%Y-%m-%d %H:%M:%S.%f')

        # Tell the datetime object that it's in UTC time zone since
        # datetime objects are 'naive' by default
        utc = utc.replace(tzinfo=from_zone)

        # Convert time zone
        result.append(utc.astimezone(to_zone))

    return result


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
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    form = UpgradeBalanceForm()
    if form.validate_on_submit():
        amount = float(form.amount.data.replace(",", "."))
        if amount < 0.0:
            flash("Opwaardering kan niet negatief zijn!", "danger")
            return render_template('upgrade.html', title='Opwaarderen', form=form)
        db_handler.addbalance(form.user.data, amount)
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
    for t in transactions:
        print(t.timestamp)
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
    quantity = 1
    db_handler.addpurchase(drinkid, userid, quantity)
    return redirect(url_for('index'))

# Input in format of <userid>a<amount>&...
@app.route('/drink/<int:drink_id>/<string:cart>')
def purchase_from_cart(drink_id, cart):
    for order in cart.split('&'):
        data = order.split('a')
        db_handler.addpurchase(drink_id, int(data[0]), int(data[1]))
    return redirect(url_for('index'))

'''@app.route('/testforms', methods=['GET', 'POST'])
def test():
    form = DrinkForm()
    if form.validate_on_submit():
        product = Product(name=form.name.data, price=form.price.data, purchaseable=True)
        db.session.add(product)
        db.session.commit()
        image = form.image.data
        filename = secure_filename(image.filename)
        flash("filename: {}".format(str(filename)))
        print(str(filename))
        filename.save(os.path.join(app.instance_path,'products', filename))
        flash("Product {} succesvol aangemaakt".format(product.name))
        return redirect(url_for('admin'))
    return render_template('testforms.html', form=form)'''

##
#
# Admin Panel
#
##

@app.route('/admin', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin', 'Beheerderspaneel', order=1)
def admin():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    return render_template('admin/admin.html', title='Admin paneel')

@app.route('/admin/users', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.users', 'Gebruikersbeheer', order=2)
def admin_users():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    form = UserRegistrationForm()
    if form.validate_on_submit():
        db_handler.adduser(form.name.data, form.group.data)
        return redirect(url_for('admin_users'))
    return render_template("admin/manusers.html", title="Gebruikersbeheer", backurl=url_for('index'), User=User, Usergroup=Usergroup, form=form)

@app.route('/admin/users/delete/<int:userid>')
def admin_users_delete(userid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    user = User.query.get(userid)
    if user.balance == 0.0:
        message = "gebruiker " + user.name + " wilt verwijderen? Alle historie gaat hierbij verloren!"
        agree_url = url_for("admin_users_delete_exec", userid=userid)
        return_url = url_for("admin_users")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url, return_url=return_url)
    else:
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:userid>/exec')
def admin_users_delete_exec(userid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    if (User.query.get(userid).balance != 0.0):
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))
    db_handler.deluser(userid)
    return redirect(url_for('admin_users'))

@app.route('/admin/transactions')
@register_breadcrumb(app, '.admin.transactions', 'Transactiebeheer', order=2)
def admin_transactions():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    transactions = Transaction.query.all()
    return render_template('admin/mantransactions.html', User=User, transactions=transactions, Purchase=Purchase, Product=Product)

@app.route('/admin/transactions/delete/<int:tranid>')
def admin_transactions_delete(tranid):
    transaction = Transaction.query.get(tranid)
    message = "transactie met ID " + str(transaction.id) + " wilt verwijderen?"
    agree_url = url_for("admin_transactions_delete_exec", tranid=tranid)
    return_url = url_for("admin_transactions")
    return render_template("verify.html", title="Bevestigen", message=message, transaction=transaction, agree_url=agree_url, return_url=return_url)

@app.route('/admin/transactions/delete/<int:tranid>/exec')
def admin_transactions_delete_exec(tranid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    db_handler.delpurchase(tranid)
    return redirect(url_for('admin_transactions'))

@app.route('/admin/drinks', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks', 'Productbeheer', order=2)
def admin_drinks():
    drinks = Product.query.all()
    form = DrinkForm()
    if form.validate_on_submit():
        db_handler.adddrink(form.name.data, float(form.price.data.replace(",", ".")), form.image.data)
        return redirect(url_for('admin_drinks'))
    return render_template('admin/mandrinks.html', drinks=drinks, form=form)

@app.route('/admin/drinks/edit/<int:drinkid>', methods=['GET', 'POST'])
def admin_drinks_edit(drinkid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    form = ChangeDrinkForm()
    form2 = ChangeDrinkImageForm()
    if form.submit1.data and form.validate_on_submit():
        db_handler.editdrink_attr(drinkid, form.name.data, float(form.price.data.replace(",", ".")), form.purchaseable.data)
        return redirect(url_for('admin_drinks'))
    if form2.submit2.data and form2.validate_on_submit():
        db_handler.editdrink_image(drinkid, form2.image.data)
        return redirect(url_for('admin_drinks'))
    return render_template('admin/editdrink.html', product=Product.query.get(drinkid), form=form, form2=form2)

@app.route('/admin/drinks/delete/<int:drinkid>')
def admin_drinks_delete(drinkid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    db_handler.deldrink(drinkid)
    return redirect(url_for('admin_drinks'))

@app.route('/admin/usergroups', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.usergroups', 'Groepenbeheer', order=2)
def admin_usergroups():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    form = UserGroupRegistrationForm()
    if form.validate_on_submit():
        db_handler.addusergroup(form.name.data)
        return redirect(url_for('admin_usergroups'))
    return render_template("admin/manusergroups.html", title="Groepen", form=form, Usergroup=Usergroup)

@app.route('/admin/usergroups/delete/<int:usergroupid>')
def admin_usergroups_delete(usergroupid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    usergroup = Usergroup.query.get(usergroupid)
    users = usergroup.users.all()
    if len(users) == 0:
        message = "groep " + usergroup.name + " wilt verwijderen?"
        agree_url = url_for("admin_usergroups_delete_exec", usergroupid=usergroupid)
        return_url = url_for("admin_usergroups")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url, return_url=return_url)
    else:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))

@app.route('/admin/usergroups/delete/<int:usergroupid>/exec')
def admin_usergroups_delete_exec(usergroupid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    if len(Usergroup.query.get(usergroupid).users.all()) != 0:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))
    db_handler.delusergroup(usergroupid)
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

    def barplot_drinks(df):
        D = count_plot(df)

        fig1 = plt.figure()
        ax1 = plt.gca()
        bars = ax1.bar(range(len(D)), list(D.values()), align='center', color=plotcolours)
        ax1.set_xticks(range(len(D.values())))
        ax1.set_xticklabels([Product.query.get(x).name for x in D.keys()])
        yint = range(int(min(D.values())), int(max(D.values())+1))
        ax1.set_yticks(yint)
        ax1.set_title("Aantal bestelde producten")
        fig1.savefig('app/static/graphs/plot-bar-user-{}.png'.format(userid), transparent=True)

    def piechart_drinks(df):
        D = count_plot(df)

        fig = plt.figure()
        ax = plt.gca()
        pies = ax.pie(list(D.values()), colors=plotcolours, explode=[0.02]*len(D.values()), labels=[Product.query.get(x).name for x in D.keys()], autopct=make_autopct(list(D.values())))
        ax.set_title("Aantal bestelde producten")
        fig.savefig('app/static/graphs/plot-pie-user-{}.png'.format(userid), transparent=True)

    def barchart_drinkspermonth():
        df1 = query_to_dataframe(user.transactions.filter(Transaction.upgrade_id == None).all(), ["timestamp", "balchange"])
        df1_1 = df1.groupby(pd.Grouper(key="timestamp", freq="M")).sum()
        df2 = query_to_dataframe(user.transactions.filter(Transaction.purchase_id == None).all(), ["timestamp", "balchange"])
        df2_1 = df2.groupby(pd.Grouper(key='timestamp', freq='M')).sum()

        fig = plt.figure()
        ax = plt.gca()
        bars1 = ax.bar(range(len(df1_1)), abs(df1_1['balchange']), align='center', color=plotcolours[0])
        bars2 = ax.bar(range(len(df2_1)))

        fig.savefig('app/static/graphs/plot-barmonth-user-{}.png'.format(userid), transparent=True)

    def linechart_money(df):
        df = query_to_dataframe(user.transactions.all(), ["timestamp", "newbal", "balchange"])

    thread1 = Thread(target=barplot_drinks, args=(query_to_dataframe(user.purchases.all(), ["product_id", "amount", "price"]), ))
    thread2 = Thread(target=piechart_drinks, args=(query_to_dataframe(user.purchases.all(), ["product_id", "amount", "price"]), ))
    thread1.start()
    thread2.start()
    thread1.join()
    filenames.append("graphs/plot-bar-user-{}.png".format(userid))
    thread2.join()
    filenames.append("graphs/plot-pie-user-{}.png".format(userid))


    return render_template('stats/statsuser.html', title="Statistieken voor {}".format(user.name), user=user, filenames=filenames)

@app.route('/stats/drink/<int:drinkid>')
def stats_drink(drinkid):
    return None

