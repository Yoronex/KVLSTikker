from typing import Dict, Any

from threading import Thread
from flask import render_template, flash, redirect, url_for, request, abort, jsonify, json, make_response
from sqlalchemy import and_, or_, func
from app import app
from app.dbhandler import dbhandler
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm, \
    ChangeDrinkForm, ChangeDrinkImageForm, AddInventoryForm, PayOutProfitForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction, Inventory
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb
import pandas as pd
import copy
import collections
import spotipy
from spotipy import oauth2
import spotipy.util as util

from datetime import datetime, timedelta
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


def query_to_dataframe(query, columns):
    nestedDict = {}
    for q in query:
        nestedDict[q.id] = q.__dict__
    return pd.DataFrame.from_dict(nestedDict, orient="index", columns=columns)


def make_autopct(values):
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct * total / 100.0))
        return '{p:.2f}%  ({v:d})'.format(p=pct, v=val)

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


def get_inventory(product_id):
    inventory = Inventory.query.filter(product_id=product_id).all()
    sum = 0
    for i in inventory:
        sum = sum + inventory.quantity
    return sum


def get_usergroups_with_users():
    usergroups = Usergroup.query.all()
    for g in usergroups:
        if len(g.users.all()) == 0:
            usergroups.remove(g)
    return usergroups


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


plotcolours = ["#0b8337", "#ffd94a", "#707070"]

birthday = False
showed_birthdays = True
birthdays = db_handler.is_birthday()
if len(birthdays) > 0:
    birthday = True
    showed_birthdays = False


@app.route('/')
@app.route('/index')
@app.route('/drink')
@register_breadcrumb(app, '.', 'Home', order=0)
@register_breadcrumb(app, '.drink', 'Product', order=1)
def index():
    if 'confetti' not in request.cookies and birthday:
        resp = make_response(redirect(url_for('index')))
        resp.set_cookie('confetti', str(True))
        return resp

    resp = make_response(render_template('index.html', title='Home', h1="Kies iets uit!", birthdays=birthdays,
                           showed_birthdays=showed_birthdays, Product=Product), 200)
    resp.set_cookie('birthdays-shown', '')
    return resp


@app.route('/upgrade', methods=['GET', 'POST'])
@register_breadcrumb(app, '.upgrade', 'Opwaarderen', order=1)
def upgrade():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = UpgradeBalanceForm()
    if form.validate_on_submit():
        amount = float(form.amount.data.replace(",", "."))
        if amount < 0.0:
            flash("Opwaardering kan niet negatief zijn!", "danger")
            return render_template('upgrade.html', title='Opwaarderen', form=form)
        alert = (db_handler.addbalance(form.user.data, amount))
        flash(alert[0], alert[1])
        return redirect(url_for('index'))
    return render_template('upgrade.html', title='Opwaarderen', h1="Opwaarderen", form=form)


@app.route('/balance')
@register_breadcrumb(app, '.balance', "Saldo's", order=1)
def balance():
    usergroups = get_usergroups_with_users()
    return render_template('balance.html', title='Saldo', h1="Saldo's", usergroups=usergroups,
                           amount_usergroups=len(usergroups)), 200


@app.route('/user')
@register_breadcrumb(app, '.user', 'Gebruiker', order=1)
def users():
    return redirect(url_for('balance'))


def view_user_dlc(*args, **kwargs):
    user_id = request.view_args['userid']
    user = User.query.get(user_id)
    return [{'text': user.name, 'url': url_for('user', userid=user_id)}]


@app.route('/user/<int:userid>')
@register_breadcrumb(app, '.user.id', '', dynamic_list_constructor=view_user_dlc, order=2)
def user(userid):
    user = User.query.get(userid)
    transactions = user.transactions.order_by(Transaction.id.desc()).all()
    upgrades = user.upgrades.all()

    count = {}
    for p in user.purchases:
        if p.product_id not in count:
            count[p.product_id] = p.amount
        else:
            count[p.product_id] = count[p.product_id] + p.amount
    data = []
    for p_id, amount in count.items():
        data.append((p_id, Product.query.get(p_id).name, int(amount)))
    ids, values, labels = top10(count, data)

    return render_template('user.html', title=user.name, h1="Informatie over " + user.name, user=user,
                           transactions=transactions, Purchase=Purchase, upgrades=upgrades, Product=Product,
                           ids=ids, data=values, labels=labels, url_prefix=""), 200


@app.route('/purchasehistory')
def purchasehistory():
    return render_template('purchasehistory.html', title='Aankoophistorie', h1="Aankoophistorie", User=User,
                           Product=Product,
                           Purchase=Purchase), 200


def view_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('drink', drinkid=drink_id)}]


@app.route('/drink/<int:drinkid>', methods=['GET', 'POST'])
@register_breadcrumb(app, '.drink.id', '', dynamic_list_constructor=view_drink_dlc, order=2)
def drink(drinkid):
    drink = Product.query.get(drinkid)
    usergroups = get_usergroups_with_users()
    stats = db_handler.get_product_stats(drinkid)
    return render_template('drink.html', title=drink.name, h1="{} aftikken (€ {})".format(drink.name, ('%.2f' % drink.price).replace('.', ',')), drink=drink,
                           usergroups=usergroups, Product=Product,
                           shared=False, stats=stats, User=User), 200


@app.route('/drink/<int:drinkid>/<int:userid>')
def purchase(drinkid, userid):
    quantity = 1
    alert = (db_handler.addpurchase(drinkid, userid, quantity))
    flash(alert[0], alert[1])
    return redirect(url_for('index'))


# Input in format of <userid>a<amount>&...
@app.route('/drink/<int:drink_id>/<string:cart>')
def purchase_from_cart(drink_id, cart):
    final_alert = {}
    shared = False
    split = cart.split('&')
    if len(split) == 0:
        abort(500)
    if split[0] == "0":
        r = False
    else:
        r = True
    for order in split[1:len(split)]:
        data = order.split('a')
        if data[0] == '0':
            shared = True
            amount = data[1]
        else:
            alert = (db_handler.addpurchase(drink_id, int(data[0]), int(data[1]), r))
            if alert[1] not in final_alert:
                final_alert[alert[1]] = alert[0]
            else:
                final_alert[alert[1]] = final_alert[alert[1]] + ", \n " + alert[0]
    for key, value in final_alert.items():
        flash(value, key)
    if not shared:
        return redirect(url_for('index'))
    else:
        return redirect(url_for('purchase_together', drinkid=drink_id, amount=amount))


@register_breadcrumb(app, '.drink.id.shared', 'Gezamelijk', order=3)
@app.route('/drink/<int:drinkid>/shared/<int:amount>')
def purchase_together(drinkid, amount):
    drink = copy.deepcopy(Product.query.get(drinkid))
    usergroups = get_usergroups_with_users()
    drink.price = drink.price * amount
    stats = db_handler.get_product_stats(drinkid)
    return render_template('drink.html', title=drink.name,
                           h1="Gezamenlijk " + str(amount) + " " + drink.name + " afrekenen", drink=drink,
                           usergroups=usergroups, Product=Product,
                           shared=True, stats=stats, User=User), 200


# Input in format of <userid>a<amount>&
@app.route('/drink/<int:drinkid>/shared/<int:amount>/<string:cart>')
def purchase_from_cart_together(drinkid, amount, cart):
    final_alert = {}
    denominator = 0
    split = cart.split('&')
    if len(split) == 0:
        abort(500)
    if split[0] == "0":
        r = False
    else:
        r = True
    for order in split[1:len(split)]:
        denominator = denominator + int(order.split('a')[1])

    for order in split[1:len(split)]:
        data = order.split('a')
        alert = db_handler.addpurchase(drinkid, int(data[0]), float(int(data[1])) * amount / denominator, r)
        if alert[1] not in final_alert:
            final_alert[alert[1]] = alert[0]
        else:
            final_alert[alert[1]] = final_alert[alert[1]] + ", \n " + alert[0]
    for key, value in final_alert.items():
        flash(value, key)
    return redirect(url_for('index'))


##
#
# Admin Panel
#
##

@app.route('/admin', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin', 'Beheerderspaneel', order=1)
def admin():
    if request.remote_addr != "127.0.0.1":
        abort(403)

    products = []
    for p in Product.query.filter(and_(Product.recipe_input == None), (Product.purchaseable == True)).all():
        result = db_handler.get_inventory_stock(p.id)
        result[0]['name'] = p.name
        products.append(result[0])

    transactions = {}
    t_list = []
    upgrades = Upgrade.query.all()
    purchases = Purchase.query.all()
    transactions['upgrades'] = len(upgrades)
    transactions['purchases'] = len(purchases)
    transactions['total'] = len(upgrades) + len(purchases)
    transactions['upgrades_value'] = 0
    transactions['purchases_value'] = 0
    for u in upgrades:
        transactions['upgrades_value'] = transactions['upgrades_value'] + u.amount
    for p in purchases:
        transactions['purchases_value'] = transactions['purchases_value'] + p.amount * p.price
    transactions['revenue'] = transactions['upgrades_value'] - transactions['purchases_value']

    return render_template('admin/admin.html', title='Admin paneel', h1="Beheerderspaneel", Usergroup=Usergroup,
                           products=products, transactions=transactions), 200


@app.route('/admin/users', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.users', 'Gebruikersbeheer', order=2)
def admin_users():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = UserRegistrationForm()
    if form.validate_on_submit():
        alert = (db_handler.adduser(form.name.data, form.group.data, form.profitgroup.data, form.birthday.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_users'))
    print(form.errors)
    return render_template("admin/manusers.html", title="Gebruikersbeheer", h1="Gebruikersbeheer",
                           backurl=url_for('index'), User=User,
                           Usergroup=Usergroup, form=form), 200


@app.route('/admin/users/delete/<int:userid>')
def admin_users_delete(userid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    user = User.query.get(userid)
    if user.balance == 0.0:
        message = "gebruiker " + user.name + " wilt verwijderen? Alle historie gaat hierbij verloren! <br><br>Let erop "
        agree_url = url_for("admin_users_delete_exec", userid=userid)
        return_url = url_for("admin_users")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url,
                               return_url=return_url), 200
    else:
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:userid>/exec')
def admin_users_delete_exec(userid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    if (User.query.get(userid).balance != 0.0):
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))
    #alert = (db_handler.deluser(userid))
    #flash(alert[0], alert[1])
    flash("Wegens enkele ontdekte fouten in Tikker is het verwijderen van gebruikers tijdelijk uitgeschakeld", "danger")
    return redirect(url_for('admin_users'))


@app.route('/admin/transactions')
@register_breadcrumb(app, '.admin.transactions', 'Transactiebeheer', order=2)
def admin_transactions():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    transactions = reversed(Transaction.query.all())
    return render_template('admin/mantransactions.html', title="Transactiebeheer", h1="Alle transacties", User=User,
                           transactions=transactions, Purchase=Purchase,
                           Product=Product), 200


@app.route('/admin/transactions/delete/<int:tranid>')
def admin_transactions_delete(tranid):
    transaction = Transaction.query.get(tranid)
    message = "transactie met ID " + str(transaction.id) + " wilt verwijderen?"
    agree_url = url_for("admin_transactions_delete_exec", tranid=tranid)
    return_url = url_for("admin_transactions")
    return render_template("verify.html", title="Bevestigen", message=message, transaction=transaction,
                           agree_url=agree_url, return_url=return_url), 200


@app.route('/admin/transactions/delete/<int:tranid>/exec')
def admin_transactions_delete_exec(tranid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    alert = (db_handler.deltransaction(tranid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_transactions'))


@app.route('/admin/drinks', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks', 'Productbeheer', order=2)
def admin_drinks():
    form = DrinkForm()
    if request.method == "POST":
        if form.validate_on_submit():
            alert = (db_handler.adddrink(form.name.data, float(form.price.data.replace(",", ".")), int(form.pos.data), form.image.data,
                                         form.hoverimage.data, form.recipe.data, form.inventory_warning.data, form.alcohol.data, form.volume.data, form.unit.data))
            flash(alert[0], alert[1])
            return redirect(url_for('admin_drinks'))
        else:
            flash(form.errors, "danger")
    return render_template('admin/mandrinks.html', title="Productbeheer", h1="Productbeheer", Product=Product,
                           form=form), 200


def view_admin_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('admin_drinks_edit', drinkid=drink_id)}]


@app.route('/admin/drinks/edit/<int:drinkid>', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks.id', '', dynamic_list_constructor=view_admin_drink_dlc, order=3)
def admin_drinks_edit(drinkid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = ChangeDrinkForm()
    form2 = ChangeDrinkImageForm()
    recipe = ""
    product = Product.query.get(drinkid)
    if product.recipe_input is not None:
        for key, value in product.recipe_input.items():
            recipe = recipe + str(value) + "x" + str(key) + ", "

    if form.submit1.data and form.validate_on_submit():
        alert = (db_handler.editdrink_attr(drinkid, form.name.data, float(form.price.data.replace(",", ".")), int(form.pos.data),
                                           form.purchaseable.data, form.recipe.data, form.inventory_warning.data, form.alcohol.data, form.volume.data, form.unit.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    if form2.submit2.data and form2.validate_on_submit():
        alert = (db_handler.editdrink_image(drinkid, form2.image.data, form2.hoverimage.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    return render_template('admin/editdrink.html', title="{} bewerken".format(product.name),
                           h1="Pas {} (ID: {}) aan".format(product.name, product.id), product=product, form=form,
                           form2=form2, recipe=recipe[:-2]), 200


@app.route('/admin/drinks/delete/<int:drinkid>')
def admin_drinks_delete(drinkid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    alert = (db_handler.deldrink(drinkid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_drinks'))


@app.route('/admin/usergroups', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.usergroups', 'Groepenbeheer', order=2)
def admin_usergroups():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = UserGroupRegistrationForm()
    if form.validate_on_submit():
        alert = (db_handler.addusergroup(form.name.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_usergroups'))
    return render_template("admin/manusergroups.html", title="Groepen", h1="Groepenbeheer", form=form,
                           Usergroup=Usergroup), 200


@app.route('/admin/usergroups/delete/<int:usergroupid>')
def admin_usergroups_delete(usergroupid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    usergroup = Usergroup.query.get(usergroupid)
    users = usergroup.users.all()
    if len(users) == 0:
        message = "groep " + usergroup.name + " wilt verwijderen?"
        agree_url = url_for("admin_usergroups_delete_exec", usergroupid=usergroupid)
        return_url = url_for("admin_usergroups")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url,
                               return_url=return_url), 200
    else:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))


@app.route('/admin/usergroups/delete/<int:usergroupid>/exec')
def admin_usergroups_delete_exec(usergroupid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    if len(Usergroup.query.get(usergroupid).users.all()) != 0:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))
    alert = (db_handler.delusergroup(usergroupid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_usergroups'))


@register_breadcrumb(app, '.admin.inventory', 'Inventarisbeheer', order=2)
@app.route('/admin/inventory/', methods=['GET', 'POST'])
def admin_inventory():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = AddInventoryForm()
    if form.validate_on_submit():
        alert = (db_handler.add_inventory(int(form.product.data), int(form.quantity.data),
                                          float(form.purchase_price.data.replace(",", ".")), form.note.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_inventory'))

    return render_template("admin/maninventory.html", title="Inventarisbeheer", h1="Inventarisbeheer",
                           backurl=url_for('index'), Product=Product,
                           Inventory=Inventory, form=form), 200


@register_breadcrumb(app, '.admin.inventorycorrect', 'Inventariscorrectie', order=2)
@app.route('/admin/inventory/correct', methods=['GET', 'POST'])
def admin_correct_inventory():
    products = [p.serialize for p in Product.query.filter(Product.recipe_input == None).all()]
    for p in products:
        p['stock'] = db_handler.calcStock(p['id'])

    if request.method == 'POST':
        result = db_handler.correct_inventory(request.get_json())
        if type(result) is tuple:
            flash(result[0], result[1])
        return redirect(url_for('admin'), code=302)

    inventories = [i.serialize for i in Inventory.query.filter(Inventory.quantity != 0).all()]
    usergroup_ids = {g.id: g.name for g in Usergroup.query.all()}
    return render_template("admin/inventorycorrection.html", title="Inventaris correctie", h1="Inventaris correctie",
                           Product=Product, products=products, Usergroup=Usergroup, inventories=inventories, usergroup_ids=usergroup_ids)


@register_breadcrumb(app, '.admin.profit', 'Winst uitkeren', order=2)
@app.route('/admin/profit', methods=['GET', 'POST'])
def payout_profit():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = PayOutProfitForm()
    if form.validate_on_submit():
        alert = db_handler.payout_profit(int(form.usergroup.data), float(form.amount.data.replace(",", ".")),
                                         form.verification.data)
        flash(alert[0], alert[1])
        return redirect(url_for('payout_profit'))
    return render_template("admin/manprofit.html", title="Winst uitkeren", h1="Winst uitkeren", Usergroup=Usergroup,
                           form=form), 200


@app.route('/tog_confetti', methods=['GET'])
def tog_confetti():
    resp = redirect(url_for('index'))
    if 'confetti' in request.cookies:
        if request.cookies.get('confetti') == str(True):
            resp.set_cookie('confetti', str(False))
        else:
            resp.set_cookie('confetti', str(True))
    else:
        resp.set_cookie('confetti', str(True))
    return resp


@app.route('/dark')
def enable_darkmode():
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie("dark-mode", str(True))
    return resp

@app.route('/force')
def force_execute():
    db_handler.force_edit()
    return "succes"


##
#
# Statistieken
#
##



'''
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
        yint = range(int(min(D.values())), int(max(D.values()) + 1))
        ax1.set_yticks(yint)
        ax1.set_title("Aantal bestelde producten")
        fig1.savefig('app/static/graphs/plot-bar-user-{}.png'.format(userid), transparent=True)

    def piechart_drinks(df):
        D = count_plot(df)

        fig = plt.figure()
        ax = plt.gca()
        pies = ax.pie(list(D.values()), colors=plotcolours, explode=[0.02] * len(D.values()),
                      labels=[Product.query.get(x).name for x in D.keys()], autopct=make_autopct(list(D.values())))
        ax.set_title("Aantal bestelde producten")
        fig.savefig('app/static/graphs/plot-pie-user-{}.png'.format(userid), transparent=True)

    def barchart_drinkspermonth():
        df1 = query_to_dataframe(user.transactions.filter(Transaction.upgrade_id == None).all(),
                                 ["timestamp", "balchange"])
        df1_1 = df1.groupby(pd.Grouper(key="timestamp", freq="M")).sum()
        df2 = query_to_dataframe(user.transactions.filter(Transaction.purchase_id == None).all(),
                                 ["timestamp", "balchange"])
        df2_1 = df2.groupby(pd.Grouper(key='timestamp', freq='M')).sum()

        fig = plt.figure()
        ax = plt.gca()
        bars1 = ax.bar(range(len(df1_1)), abs(df1_1['balchange']), align='center', color=plotcolours[0])
        bars2 = ax.bar(range(len(df2_1)))

        fig.savefig('app/static/graphs/plot-barmonth-user-{}.png'.format(userid), transparent=True)

    def linechart_money(df):
        df = query_to_dataframe(user.transactions.all(), ["timestamp", "newbal", "balchange"])

    thread1 = Thread(target=barplot_drinks,
                     args=(query_to_dataframe(user.purchases.all(), ["product_id", "amount", "price"]),))
    thread2 = Thread(target=piechart_drinks,
                     args=(query_to_dataframe(user.purchases.all(), ["product_id", "amount", "price"]),))
    thread1.start()
    thread2.start()
    thread1.join()
    filenames.append("graphs/plot-bar-user-{}.png".format(userid))
    thread2.join()
    filenames.append("graphs/plot-pie-user-{}.png".format(userid))

    return render_template('stats/statsuser.html', title="Statistieken voor {}".format(user.name), user=user,
                           filenames=filenames)

'''


def getStatValue(elem):
    return elem[2]


def top10(count, data):
    data.sort(key=getStatValue, reverse=True)
    if len(count) <= 10:
        size = len(count)
    else:
        size = 9

    ids = [data[i][0] for i in range(0, size)]
    labels = [data[i][1] for i in range(0, size)]
    values = [data[i][2] for i in range(0, size)]

    if len(count) - size >= 2:
        sum = 0
        for i in range(size, len(count)):
            sum = sum + data[i][1]
        ids.append(0)
        values.append(sum)
        labels.append("Overig")

    return ids, values, labels

@register_breadcrumb(app, '.stats', 'Statistieken', order=1)
@register_breadcrumb(app, '.stats.drink', 'Producten', order=2)
@register_breadcrumb(app, '.stats.user', 'Gebruikers', order=2)
@register_breadcrumb(app, '.stats.group', 'Groepen', order=2)
@app.route('/stats')
def stats():
    return render_template('/stats/stats.html', title='Statistieken', h1='Statistieken', Product=Product, User=User)


@app.route('/stats/user/<int:userid>')
def stats_user_redirect(userid):
    return redirect(url_for('stats_user', userid=userid, begindate=app.config['STATS_BEGINDATE'], enddate=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")))


def getIDnumber(elem):
    return elem[0]


@register_breadcrumb(app, '.stats.user.id', '', dynamic_list_constructor=view_user_dlc, order=3)
@app.route('/stats/user/<int:userid>/<string:begindate>/<string:enddate>')
def stats_user(userid, begindate, enddate):
    user = User.query.get(userid)
    count = {}
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")
    purchases = Purchase.query.filter(and_(Purchase.user_id == userid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend)).all()
    transactions = Transaction.query.filter(and_(Transaction.user_id == userid, Transaction.timestamp >= parsedbegin, Transaction.timestamp <= parsedend)).all()


    for p in purchases:
        if p.product_id not in count:
            count[p.product_id] = p.amount
        else:
            count[p.product_id] = count[p.product_id] + p.amount

    datat = []
    for t in transactions:
        datat.append({
            "x": str(t.timestamp.strftime("%Y-%m-%d %H:%M:%S")),
            "y": t.newbal
        })

    data = []
    for p_id, amount in count.items():
        data.append((p_id, Product.query.get(p_id).name, int(amount)))
    ids, values, labels = top10(count, data)

    countw = {}
    for date in (parsedbegin + timedelta(n) for n in range(0, (parsedend - parsedbegin).days)):
        countw[int(date.strftime('%V'))] = 0

    for t in transactions:
        if t.balchange <= 0:
            if int(t.timestamp.strftime('%V')) not in countw:
                countw[int(t.timestamp.strftime('%V'))] = -t.balchange
            else:
                countw[int(t.timestamp.strftime('%V'))] = countw[int(t.timestamp.strftime('%V'))] - t.balchange
    dataw = []
    for week, amount in countw.items():
        dataw.append((week, "Week {}".format(week), amount))
    dataw.sort(key=getIDnumber, reverse=False)
    idw = [dataw[i][0] for i in range(0, len(dataw))]
    labelw = [dataw[i][1] for i in range(0, len(dataw))]
    valuew = [dataw[i][2] for i in range(0, len(dataw))]


    return render_template("stats/statsuser.html", title="Statistieken van " + user.name, h1="Statistieken van " + user.name, ids=ids, data=values, labels=labels, idw=idw, labelw=labelw, valuew=valuew,
                           datat=datat, lefturl="", righturl="", begindate=begindate, enddate=enddate), 200


def view_stats_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('stats_drink_redirect', drinkid=drink_id)}]


@app.route('/stats/drink/<int:drinkid>')
def stats_drink_redirect(drinkid):
    return redirect(url_for('stats_drink', drinkid=drinkid, begindate=app.config['STATS_BEGINDATE'], enddate=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")))


@register_breadcrumb(app, '.stats.drink.id', '', dynamic_list_constructor=view_stats_drink_dlc, order=3)
@app.route('/stats/drink/<int:drinkid>/<string:begindate>/<string:enddate>')
def stats_drink(drinkid, begindate, enddate):
    product = Product.query.get(drinkid)
    count = {}
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")
    purchases = Purchase.query.filter(and_(Purchase.product_id == drinkid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend)).all()

    for pur in purchases:
        if pur.user_id not in count:
            count[pur.user_id] = pur.amount
        else:
            count[pur.user_id] = count[pur.user_id] + pur.amount

    count_groups = {}
    for u_id, amount in count.items():
        group = User.query.get(u_id).usergroup_id
        if group not in count_groups:
            count_groups[group] = amount
        else:
            count_groups[group] = count_groups[group] + amount

    datau = []
    for u_id, amount in count.items():
        datau.append((u_id, User.query.get(u_id).name, int(amount)))
    idsu, valuesu, labelsu = top10(count, datau)

    datag = []
    for g_id, amount in count_groups.items():
        datag.append((g_id, Usergroup.query.get(g_id).name, int(amount)))
    idsg, valuesg, labelsg = top10(count_groups, datag)

    return render_template("stats/statsproduct.html", title='Statistieken over {}'.format(product.name), h1='Statistieken over {}'.format(product.name),
                           begindate=begindate, enddate=enddate, idsu=idsu, valuesu=valuesu, labelsu=labelsu, idsg=idsg, valuesg=valuesg, labelsg=labelsg,
                           lefturl="", righturl=url_for("stats_drink_group_redirect", drinkid=drinkid, groupid=0)), 200


def view_stats_drink_group_dlc(*args, **kwargs):
    group_id = request.view_args['groupid']
    usergroup = Usergroup.query.get(group_id)
    return [{'text': usergroup.name, 'url': url_for('stats_drink_group_redirect', drinkid=request.view_args['drinkid'], groupid=group_id)}]


@app.route('/stats/drink/<int:drinkid>/group/<int:groupid>')
def stats_drink_group_redirect(drinkid, groupid):
    return redirect(url_for('stats_drink_group', drinkid=drinkid, groupid=groupid, begindate=app.config['STATS_BEGINDATE'], enddate=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")))


@register_breadcrumb(app, '.stats.drink.id.group', '', dynamic_list_constructor=view_stats_drink_group_dlc, order=3)
@app.route('/stats/drink/<int:drinkid>/group/<int:groupid>/<string:begindate>/<string:enddate>')
def stats_drink_group(drinkid, groupid, begindate, enddate):
    product = Product.query.get(drinkid)
    usergroup = Usergroup.query.get(groupid)
    count = {}
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")
    purchases = Purchase.query.filter(and_(Purchase.product_id == drinkid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend)).all()

    for pur in purchases:
        if User.query.get(pur.user_id).usergroup_id == groupid:
            if pur.user_id not in count:
                count[pur.user_id] = pur.amount
            else:
                count[pur.user_id] = count[pur.user_id] + pur.amount

    count_groups = {}
    for u_id, amount in count.items():
        group = User.query.get(u_id).usergroup_id
        if group not in count_groups:
            count_groups[group] = amount
        else:
            count_groups[group] = count_groups[group] + amount

    datau = []
    for u_id, amount in count.items():
        datau.append((u_id, User.query.get(u_id).name, int(amount)))
    idsu, valuesu, labelsu = top10(count, datau)

    datag = []
    for g_id, amount in count_groups.items():
        datag.append((g_id, Usergroup.query.get(g_id).name, int(amount)))
    idsg, valuesg, labelsg = top10(count_groups, datag)

    return render_template("stats/statsproduct.html", title='Statistieken over {} voor {}'.format(product.name, usergroup.name), h1='Statistieken over {} voor {}'.format(product.name, usergroup.name),
                           begindate=begindate, enddate=enddate, idsu=idsu, valuesu=valuesu, labelsu=labelsu, idsg=idsg, valuesg=valuesg, labelsg=labelsg,
                           lefturl="", righturl=""), 200


@app.route('/test/exception')
def throw_exception():
    len(None)
    return


@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    shutdown_server()
    app.logger.info('Tikker shutting down')
    return render_template('error.html', title="Tikker wordt afgesloten...", h1="Uitschakelen", message="Tikker wordt nu afgesloten. Je kan dit venster sluiten.", gif_url="")


@app.route('/error/403')
def show_401():
    message = "Je bezoekt Tikker niet vanaf de computer waar Tikker op is geïnstalleerd. Je hebt daarom geen toegang tot deze pagina."
    gif = url_for('.static', filename='img/403.mp4')
    return render_template('error.html', title="403", h1="Error 403", message=message, gif_url=gif), 403


@app.route('/error/404')
def show_404():
    message = "Deze pagina bestaat (nog) niet! Klik op het KVLS logo links om terug te gaan naar het hoofdmenu."
    gif = url_for('.static', filename='img/404.mp4')
    return render_template('error.html', title="404", h1="Error 404", message=message, gif_url=gif), 404


@app.route('/error/500')
def show_500():
    message = "Achter de schermen is iets helemaal fout gegaan! Om dit probleem in de toekomst niet meer te zien, stuur aub berichtje naar Roy met wat je aan het doen was in Tikker toen deze foutmelding verscheen, zodat hij opgelost kan worden!"
    gif = url_for('.static', filename='img/500.mp4')
    return render_template('error.html', title="500", h1="Error 500", message=message, gif_url=gif), 500


@app.errorhandler(403)
def no_access_error(error):
    message = "Je bezoekt Tikker niet vanaf de computer waar Tikker op is geïnstalleerd. Je hebt daarom geen toegang tot deze pagina."
    gif = url_for('.static', filename='img/403.mp4')
    return render_template('error.html', title="403", h1="Error 403", message=message, gif_url=gif), 403


@app.errorhandler(404)
def not_found_error(error):
    message = "Deze pagina bestaat (nog) niet! Klik op het KVLS logo links om terug te gaan naar het hoofdmenu."
    gif = url_for('.static', filename='img/404.mp4')
    return render_template('error.html', title="404", h1="Error 404", message=message, gif_url=gif), 404


@app.errorhandler(500)
def exception_error(error):
    message = "Achter de schermen is iets helemaal fout gegaan! Om dit probleem in de toekomst niet meer te zien, stuur aub berichtje naar Roy met wat je aan het doen was in Tikker toen deze foutmelding verscheen, zodat hij opgelost kan worden!"
    gif = url_for('.static', filename='img/500.mp4')
    db_handler.rollback()
    return render_template('error.html', title="500", h1="Error 500", message=message, gif_url=gif), 500


app.config["BOOTSTRAP_SERVE_LOCAL"] = True


@app.route("/api/ping")
def server_status():
    return jsonify({"pong": "pong"})


########################
##                    ##
##   Big-Screen API   ##
##                    ##
########################


spotify_token = None
spotify = None
SPOTIPY_CLIENT_ID = 'e81cc50c967a4c64a8073d678f7b6503'
SPOTIPY_CLIENT_SECRET = 'c8d84aec8a6d4197b5eca4991ba7694b'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5000/spotifylogin'
SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'
CACHE = '.spotipyoauthcache'
sp_oauth = oauth2.SpotifyOAuth(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE, cache_path=CACHE)


@app.route("/spotifylogin")
def login_to_spotify():

    access_token = ""

    token_info = sp_oauth.get_cached_token()

    if token_info:
        print("Found cached token!")
        access_token = token_info['access_token']
    else:
        url = request.url
        code = sp_oauth.parse_response_code(url)
        if code:
            print("Found Spotify auth code in Request URL! Trying to get valid access token...")
            token_info = sp_oauth.get_access_token(code)
            access_token = token_info['access_token']

    if access_token:
        print("Access token available! Trying to get user information...")
        sp = spotipy.Spotify(access_token)
        results = sp.current_user()
        flash("Ingelogd op Spotify als {}".format(results['display_name']), "success")
        return redirect(url_for('index'))

    else:
        return redirect(sp_oauth.get_authorize_url())
