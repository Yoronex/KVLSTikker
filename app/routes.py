from typing import Dict, Any

from threading import Thread
from flask import render_template, flash, redirect, url_for, request
from sqlalchemy import and_
from app import app
from app.dbhandler import dbhandler
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm, \
    ChangeDrinkForm, ChangeDrinkImageForm, AddInventoryForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction, Inventory
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb
import pandas as pd
import copy
import collections

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


plotcolours = ["#0b8337", "#ffd94a", "#707070"]


@app.route('/')
@app.route('/index')
@app.route('/drink')
@register_breadcrumb(app, '.', 'Home', order=0)
@register_breadcrumb(app, '.drink', 'Product', order=1)
def index():
    return render_template('index.html', title='Home', h1="Kies iets uit!",  Product=Product)


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
        alert = (db_handler.addbalance(form.user.data, amount))
        flash(alert[0], alert[1])
        return redirect(url_for('index'))
    return render_template('upgrade.html', title='Opwaarderen', h1="Opwaarderen", form=form)


@app.route('/balance')
@register_breadcrumb(app, '.balance', "Saldo's", order=1)
def balance():
    usergroups = Usergroup.query.all()
    return render_template('balance.html', title='Saldo', h1="Saldo's", usergroups=usergroups, amount_usergroups=len(usergroups))


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
    return render_template('user.html', title=user.name, h1="Informatie over " + user.name, user=user, transactions=transactions, Purchase=Purchase, upgrades=upgrades,
                           Product=Product)


@app.route('/purchasehistory')
def purchasehistory():
    return render_template('purchasehistory.html', title='Aankoophistorie', h1="Aankoophistorie", User=User, Product=Product,
                           Purchase=Purchase)


@app.route('/drink/<int:drinkid>', methods=['GET', 'POST'])
@register_breadcrumb(app, '.drink.id', '', dynamic_list_constructor=view_drink_dlc, order=2)
def drink(drinkid):
    drink = Product.query.get(drinkid)
    usergroups = Usergroup.query.all()
    return render_template('drink.html', title=drink.name, h1=drink.name + " afrekenen", drink=drink, usergroups=usergroups,
                           amount_usergroups=len(usergroups), shared=False, stock=db_handler.get_inventory_stock(drinkid))


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

    for order in cart.split('&'):
        data = order.split('a')
        if data[0] == '0':
            shared = True
            amount = data[1]
        else:
            alert = (db_handler.addpurchase(drink_id, int(data[0]), int(data[1])))
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
    usergroups = Usergroup.query.all()
    drink.price = drink.price * amount
    return render_template('drink.html', title=drink.name, h1="Gezamelijk "+ str(amount) + " " + drink.name + " afrekenen", drink=drink, usergroups=usergroups,
                           amount_usergroups=len(usergroups), shared=True, stock=db_handler.get_inventory_stock(drinkid))

# Input in format of <userid>a<amount>&
@app.route('/drink/<int:drinkid>/shared/<int:amount>/<string:cart>')
def purchase_from_cart_together(drinkid, amount, cart):
    final_alert = {}
    denominator = 0
    for order in cart.split('&'):
        denominator = denominator + int(order.split('a')[1])

    for order in cart.split('&'):
        data = order.split('a')
        alert = db_handler.addpurchase(drinkid, int(data[0]), float(int(data[1])) * amount / denominator)
        if alert[1] not in final_alert:
            final_alert[alert[1]] = alert[0]
        else:
            final_alert[alert[1]] = final_alert[alert[1]] + ", \n " + alert[0]
    for key, value in final_alert.items():
        flash(value, key)
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

    products = []
    for p in Product.query.filter(and_(Product.components == None), (Product.purchaseable == True)).all():
        result = db_handler.get_inventory_stock(p.id)
        result['name'] = p.name
        products.append(result)

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

    return render_template('admin/admin.html', title='Admin paneel', h1="Beheerderspaneel", Usergroup=Usergroup, products=products, transactions=transactions)


@app.route('/admin/users', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.users', 'Gebruikersbeheer', order=2)
def admin_users():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    form = UserRegistrationForm()
    if form.validate_on_submit():
        alert = (db_handler.adduser(form.name.data, form.group.data, form.profitgroup.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_users'))
    return render_template("admin/manusers.html", title="Gebruikersbeheer", h1="Gebruikersbeheer", backurl=url_for('index'), User=User,
                           Usergroup=Usergroup, form=form)


@app.route('/admin/users/delete/<int:userid>')
def admin_users_delete(userid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    user = User.query.get(userid)
    if user.balance == 0.0:
        message = "gebruiker " + user.name + " wilt verwijderen? Alle historie gaat hierbij verloren!"
        agree_url = url_for("admin_users_delete_exec", userid=userid)
        return_url = url_for("admin_users")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url,
                               return_url=return_url)
    else:
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:userid>/exec')
def admin_users_delete_exec(userid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    if (User.query.get(userid).balance != 0.0):
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))
    alert = (db_handler.deluser(userid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_users'))


@app.route('/admin/transactions')
@register_breadcrumb(app, '.admin.transactions', 'Transactiebeheer', order=2)
def admin_transactions():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    transactions = reversed(Transaction.query.all())
    return render_template('admin/mantransactions.html', title="Transactiebeheer", h1="Alle transacties", User=User, transactions=transactions, Purchase=Purchase,
                           Product=Product)


@app.route('/admin/transactions/delete/<int:tranid>')
def admin_transactions_delete(tranid):
    transaction = Transaction.query.get(tranid)
    message = "transactie met ID " + str(transaction.id) + " wilt verwijderen?"
    agree_url = url_for("admin_transactions_delete_exec", tranid=tranid)
    return_url = url_for("admin_transactions")
    return render_template("verify.html", title="Bevestigen", message=message, transaction=transaction,
                           agree_url=agree_url, return_url=return_url)


@app.route('/admin/transactions/delete/<int:tranid>/exec')
def admin_transactions_delete_exec(tranid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    alert = (db_handler.delpurchase(tranid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_transactions'))


@app.route('/admin/drinks', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks', 'Productbeheer', order=2)
def admin_drinks():
    drinks = Product.query.all()
    form = DrinkForm()
    if form.validate_on_submit():
        alert = (db_handler.adddrink(form.name.data, float(form.price.data.replace(",", ".")), form.image.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    return render_template('admin/mandrinks.html', title="Productbeheer", h1="Productbeheer", drinks=drinks, form=form)


@app.route('/admin/drinks/edit/<int:drinkid>', methods=['GET', 'POST'])
def admin_drinks_edit(drinkid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    form = ChangeDrinkForm()
    form2 = ChangeDrinkImageForm()
    if form.submit1.data and form.validate_on_submit():
        alert = (db_handler.editdrink_attr(drinkid, form.name.data, float(form.price.data.replace(",", ".")),
                                  form.purchaseable.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    if form2.submit2.data and form2.validate_on_submit():
        alert = (db_handler.editdrink_image(drinkid, form2.image.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    product = Product.query.get(drinkid)
    return render_template('admin/editdrink.html', title="{} bewerken".format(product.name), h1="Pas {} (ID: {}) aan".format(product.name, product.id), product=product, form=form, form2=form2)


@app.route('/admin/drinks/delete/<int:drinkid>')
def admin_drinks_delete(drinkid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    alert = (db_handler.deldrink(drinkid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_drinks'))


@app.route('/admin/usergroups', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.usergroups', 'Groepenbeheer', order=2)
def admin_usergroups():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    form = UserGroupRegistrationForm()
    if form.validate_on_submit():
        alert = (db_handler.addusergroup(form.name.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_usergroups'))
    return render_template("admin/manusergroups.html", title="Groepen", h1="Groepenbeheer", form=form, Usergroup=Usergroup)


@app.route('/admin/usergroups/delete/<int:usergroupid>')
def admin_usergroups_delete(usergroupid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    usergroup = Usergroup.query.get(usergroupid)
    users = usergroup.users.all()
    if len(users) == 0:
        message = "groep " + usergroup.name + " wilt verwijderen?"
        agree_url = url_for("admin_usergroups_delete_exec", usergroupid=usergroupid)
        return_url = url_for("admin_usergroups")
        return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url,
                               return_url=return_url)
    else:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))


@app.route('/admin/usergroups/delete/<int:usergroupid>/exec')
def admin_usergroups_delete_exec(usergroupid):
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang", h1="Geen toegang")
    if len(Usergroup.query.get(usergroupid).users.all()) != 0:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))
    alert = (db_handler.delusergroup(usergroupid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_usergroups'))


@app.route('/admin/inventory/', methods=['GET', 'POST'])
def admin_inventory():
    if request.remote_addr != "127.0.0.1":
        return render_template('401.html', title="401 Geen toegang")
    form = AddInventoryForm()
    if form.validate_on_submit():
        alert = (db_handler.add_inventory(int(form.product.data), int(form.quantity.data), float(form.purchase_price.data.replace(",", ".")), form.note.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_inventory'))

    return render_template("admin/maninventory.html", title="Inventarisbeheer", h1="Inventarisbeheer", backurl=url_for('index'), Product=Product,
                           Inventory=Inventory, form=form)


@app.route('/admin/inventory/add')
def admin_add_to_inventory():
    return


@app.route('/admin/inventory/correct')
def admin_correct_inventory():
    return


@app.route('/force')
def force_execute():
    db_handler.force_edit()
    return "succes"

##
#
# Statistieken
#
##

@app.route('/stats')
def stats():
    return None

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

@app.route('/stats/user/<int:userid>')
def stats_user(userid):
    user = User.query.get(userid)
    count = {}
    for p in user.purchases:
        if p.product_id not in count:
            count[p.product_id] = p.amount
        else:
            count[p.product_id] = count[p.product_id] + p.amount
    sorted_count = collections.OrderedDict(count)
    if len(count) < 10:
        size = len(count)
    else:
        size = 10

    labels_raw = sorted_count.keys()
    labels = []
    data = sorted_count.values()
    for i in range(0, len(labels_raw)):
        labels.append(Product.query.get(i))

    return render_template("stats/statsuser.html", title="Statistieken van " + user.name, h1="Statistieken van " + user.name, data=data, labels=labels, products=Product.query.all())

@app.route('/stats/drink/<int:drinkid>')
def stats_drink(drinkid):
    return None


app.config["BOOTSTRAP_SERVE_LOCAL"] = True
