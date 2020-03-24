from flask import render_template, flash, redirect, url_for, request, abort, jsonify, make_response
from app import app, stats, socket, spotify, socketio, dbhandler, emailhandler, cart, round_up, round_down
from app.forms import *
from app.models import *
from flask_breadcrumbs import register_breadcrumb
import copy
import os

from datetime import datetime, timedelta
from dateutil import tz

page_size = 100
pagination_range = 4


def is_filled(data):
    if data is None:
        return False
    if data == '':
        return False
    if not data:
        return False
    return True


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.Config["ALLOWED_EXTENSIONS"]


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
    spotify.logout()
    socketio.stop()
    # func = request.environ.get('werkzeug.server.shutdown')
    # if func is None:
    #    raise RuntimeError('Not running with the Werkzeug Server')
    # func()


plotcolours = ["#0b8337", "#ffd94a", "#707070"]

birthday = False
showed_birthdays = True
birthdays = dbhandler.is_birthday()
if len(birthdays) > 0:
    birthday = True
    showed_birthdays = False


def calculate_pagination_with_basequery(query, request_obj):
    # If no page id is provided...
    if request_obj.args.get('page') is None:
        # We set it to 1
        page = 1
    else:
        # Otherwise, we get it from the parameters and transform it into an integer
        page = int(request_obj.args.get('page'))
    # Get the total amount of rows for this table
    total_amount_of_entries = query.count()
    # Calculate the total amount of pages
    total_amount_of_pages = int(round_up(total_amount_of_entries / page_size, 0))
    # Calculate the offset in number of rows in a page
    offset_difference = total_amount_of_entries % page_size
    # Calculate the offset in number of pages
    offset = max(0, total_amount_of_pages - page)
    # Calculate the real offset in number of rows
    real_offset = offset * page_size - (page_size - offset_difference)
    # The offset cannot be negative, so if this is the case, we need to decrease the page size
    if real_offset < 0:
        real_page_size = page_size + real_offset
        real_offset = 0
    # If the offset is not negative, we simply copy the page size
    else:
        real_page_size = page_size
    # Create the data object that contains all necessary information
    pagination = {'pages': total_amount_of_pages,
                  'currentPage': page,
                  'minPage': max(1, int(page - pagination_range)),
                  'maxPage': min(total_amount_of_pages, page + pagination_range),
                  'offset': real_offset,
                  'pageSize': real_page_size,
                  'records': '{} ... {} van de {}'.format(page_size * (page - 1) + 1,
                                                          page_size * (page - 1) + real_page_size,
                                                          total_amount_of_entries),
                  }
    # Return this object
    return pagination


def flash_form_errors(errors):
    if len(errors.keys()) > 0:
        print(errors)
        for k, v in errors.items():
            for error in v:
                flash("Fout in formulier: {} - {}".format(k, error), "danger")


def apply_filters(query):
    if 'f_transaction_type' in request.args:
        t_type = request.args.get('f_transaction_type')
        if t_type == 'upgr':
            query = query.filter(Transaction.upgrade_id != None)
        elif t_type == 'pur':
            query = query.filter(Transaction.purchase_id != None)

    if 'f_transaction_user' in request.args and int(request.args.get('f_transaction_user')) > 0:
        query = query.filter(Transaction.user_id == int(request.args.get('f_transaction_user')))

    if 'f_transaction_product' in request.args and int(request.args.get('f_transaction_product')) > 0:
        query = query.filter(Transaction.purchase.has(product_id=int(request.args.get('f_transaction_product'))))

    if 'f_transaction_round' in request.args:
        t_round = request.args.get('f_transaction_round')
        if t_round == '1':
            query = query.filter(Transaction.purchase.has(round=True))
        elif t_round == '0':
            query = query.filter(Transaction.purchase.has(round=False))

    if 'f_user_usergroup' in request.args and int(request.args.get('f_user_usergroup')) > 0:
        query = query.filter(User.usergroup_id == int(request.args.get('f_user_usergroup')))
    if 'f_user_profitgroup' in request.args and int(request.args.get('f_user_profitgroup')) > 0:
        query = query.filter(User.profitgroup_id == int(request.args.get('f_user_profitgroup')))

    if 'f_product_category' in request.args and request.args.get('f_product_category') != 'all':
        query = query.filter(Product.category == request.args.get('f_product_category'))
    if 'f_product_purchaseable' in request.args:
        t_round = request.args.get('f_product_purchaseable')
        if t_round == '1':
            query = query.filter(Product.purchaseable == True)
        elif t_round == '0':
            query = query.filter(Product.purchaseable == False)

    return query


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

    query = user.transactions
    query = apply_filters(query)
    pagination = calculate_pagination_with_basequery(query, request)
    transactions = query.limit(pagination['pageSize']).offset(pagination['offset']).all()[::-1]
    filters = UserTransactionFilterForm()

    count = {}
    for p in user.purchases:
        if p.product_id not in count:
            count[p.product_id] = p.amount
        else:
            count[p.product_id] = count[p.product_id] + p.amount
    data = []
    for p_id, amount in count.items():
        data.append((p_id, Product.query.get(p_id).name, int(amount)))
    ids, values, labels = stats.top_n(count, data, 20)

    return render_template('user.html', title=user.name, h1="Informatie over " + user.name, user=user, filters=filters,
                           transactions=transactions, ids=ids, data=values, labels=labels, url_prefix="",
                           pag=pagination), 200


def view_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('drink', drinkid=drink_id)}]


def view_dinner_dlc(*args, **kwargs):
    dinnerid = dbhandler.settings['dinner_product_id']
    if dinnerid is not None:
        product = Product.query.get(int(dinnerid))
        return [{'text': product.name, 'url': url_for('drink', drinkid=dinnerid)}]
    else:
        raise ValueError


@app.route('/drink/<int:drinkid>', methods=['GET', 'POST'])
@register_breadcrumb(app, '.drink.id', '', dynamic_list_constructor=view_drink_dlc, order=2)
def drink(drinkid):
    dinnerid = dbhandler.settings['dinner_product_id']
    if dinnerid is None:
        raise ValueError
    elif int(dinnerid) == drinkid:
        return redirect(url_for('drink_dinner'))

    borrel_data = dbhandler.borrel_mode(drinkid)

    drink = Product.query.get(drinkid)
    usergroups = get_usergroups_with_users()
    statsdict = dbhandler.get_product_stats(drinkid)
    round_form = RoundForm()
    return render_template('drink.html', title=drink.name, roundform=round_form,
                           h1="{} aftikken (€ {})".format(drink.name, ('%.2f' % drink.price).replace('.', ',')),
                           drink=drink, borrel_data=borrel_data,
                           usergroups=usergroups, Product=Product,
                           shared=False, stats=statsdict, User=User), 200


# Input in format of <userid>a<amount>&...
@app.route('/drink/<int:drink_id>/<cart_string>')
def purchase_from_cart(drink_id, cart_string):
    msg = cart.purchase(cart_string, drink_id)
    if msg['shared'] is True:
        return redirect(url_for('purchase_together', drinkid=drink_id, amount=msg['shared_amount']))
    else:
        return redirect(url_for('index'))


@register_breadcrumb(app, '.drink.id.shared', 'Gezamelijk', order=3)
@app.route('/drink/<int:drinkid>/shared/<int:amount>')
def purchase_together(drinkid, amount):
    drink = copy.deepcopy(Product.query.get(drinkid))
    usergroups = get_usergroups_with_users()
    borrel_data = dbhandler.borrel_mode(drinkid)
    drink.price = drink.price * amount
    statsdict = dbhandler.get_product_stats(drinkid)
    return render_template('drink.html', title=drink.name, borrel_data=borrel_data, roundform=None,
                           h1="Gezamenlijk " + str(amount) + " " + drink.name + " afrekenen", drink=drink,
                           usergroups=usergroups, Product=Product,
                           shared=True, stats=statsdict, User=User), 200


# Input in format of <userid>a<amount>&
@app.route('/drink/<int:drinkid>/shared/<int:amount>/<cart_string>')
def purchase_from_cart_together(drinkid, amount, cart_string):
    cart.purchase_together(cart_string, drinkid, amount)
    return redirect(url_for('index'))


@app.route('/drink/dinner')
@register_breadcrumb(app, '.drink.dinner', '', dynamic_list_constructor=view_dinner_dlc, order=2)
def drink_dinner():
    drinkid = dbhandler.settings['dinner_product_id']
    if drinkid is None:
        raise ValueError

    drink = Product.query.get(int(drinkid))
    usergroups = get_usergroups_with_users()
    return render_template('drink_dinner.html', title=drink.name, h1="{} aftikken".format(drink.name), drink=drink,
                           usergroups=usergroups, Product=Product, shared=False, User=User), 200


@app.route('/drink/dinner/<cart_string>')
def purchase_dinner_from_cart(cart_string):
    cart.purchase_dinner(cart_string, request.args['price'], request.args['comments'])
    return redirect(url_for('index'))


@register_breadcrumb(app, '.settings', 'Browserinstellingen', order=1)
@app.route('/settings')
def client_settings():
    return render_template('settings.html', title="Browserinstellingen", h1="Browserinstellingen")


@register_breadcrumb(app, '.soundboard', 'Soundboard', order=1)
@app.route('/soundboard')
def soundboard():
    sounds = [s.serialize for s in Sound.query.all()]
    return render_template('soundboard.html', title="Soundboard", h1="Soundboard", sounds=sounds)


@register_breadcrumb(app, '.quote', 'Quote toevoegen', order=1)
@app.route('/quote', methods=['GET', 'POST'])
def add_user_quote():
    form = AddQuoteForm()

    if form.validate_on_submit():
        alert = dbhandler.addquote(form.quote.data, form.author.data)
        flash(alert[0], alert[1])
        return redirect(url_for('index'))

    return render_template('quote.html', title="Citaat toevoegen", h1="Citaat toevoegen", form=form)


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
    total_p_value = 0
    for p in Product.query.filter(and_(Product.recipe_input == None), (Product.purchaseable == True)).all():
        result = dbhandler.get_inventory_stock(p.id)
        result[0]['name'] = p.name
        result[0]['inventory_value'] = round_down(dbhandler.calc_inventory_value(p.id))
        total_p_value += result[0]['inventory_value']
        products.append(result[0])

    transactions = {}
    t_list = []
    upgrades = Upgrade.query.all()
    purchases = Purchase.query.filter(Purchase.price > 0).all()
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
                           products=products, transactions=transactions, value=total_p_value), 200


@app.route('/admin/users', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.users', 'Gebruikersbeheer', order=2)
def admin_users():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = UserRegistrationForm()
    filters = UsersFilterForm()

    query = User.query
    query = apply_filters(query)
    users = query.all()

    if form.validate_on_submit():
        alert = (dbhandler.adduser(form.name.data, form.email.data, form.group.data, form.profitgroup.data,
                                   form.birthday.data))
        flash(alert[0], alert[1])

        socket.update_stats()

        return redirect(url_for('admin_users'))
    flash_form_errors(form.errors)
    return render_template("admin/manusers.html", title="Gebruikersbeheer", h1="Gebruikersbeheer", users=users,
                           Usergroup=Usergroup, form=form, filters=filters), 200


@register_breadcrumb(app, '.admin.users.confirm', "Bevestigen", order=2)
@app.route('/admin/users/delete/<int:userid>')
def admin_users_delete(userid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    user = User.query.get(userid)
    group = Usergroup.query.get(user.usergroup_id)
    if user.balance == 0.0:
        message = "gebruiker " + user.name + "(van de groep " + group.name + ") wilt verwijderen? Alle historie gaat hierbij verloren!"
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
    # alert = (dbhandler.deluser(userid))
    # flash(alert[0], alert[1])
    flash("Wegens enkele ontdekte fouten in Tikker is het verwijderen van gebruikers tijdelijk uitgeschakeld", "danger")

    socket.update_stats()

    return redirect(url_for('admin_users'))


@app.route('/admin/transactions')
@register_breadcrumb(app, '.admin.transactions', 'Transactiebeheer', order=2)
def admin_transactions():
    if request.remote_addr != "127.0.0.1":
        abort(403)

    query = Transaction.query
    query = apply_filters(query)

    pagination = calculate_pagination_with_basequery(query, request)
    transactions = query.limit(pagination['pageSize']).offset(pagination['offset']).all()[::-1]
    filters = TransactionFilterForm()

    return render_template('admin/mantransactions.html', title="Transactiebeheer", h1="Alle transacties", User=User,
                           transactions=transactions, Purchase=Purchase, Upgrade=Upgrade, pag=pagination,
                           Product=Product, filters=filters), 200


@register_breadcrumb(app, '.admin.transactions.confirm', "Bevestigen", order=2)
@app.route('/admin/transactions/delete/<int:tranid>')
def admin_transactions_delete(tranid):
    transaction = Transaction.query.get(tranid)
    u = User.query.get(transaction.user_id)
    if transaction.purchase_id is not None:
        purchase = Purchase.query.get(transaction.purchase_id)
        product = Product.query.get(purchase.product_id)
        message = "transactie met ID " + "{} ({}x {} voor {})".format(str(transaction.id),
                                                                      str(round_up(purchase.amount)), product.name,
                                                                      u.name) + " wilt verwijderen?"
    else:
        upgr = Upgrade.query.get(transaction.upgrade_id)
        message = "transactie met ID " + "{} ({} € {} voor {})".format(str(transaction.id), upgr.description,
                                                                       round_up(upgr.amount),
                                                                       u.name) + " wilt verwijderen?"
    agree_url = url_for("admin_transactions_delete_exec", tranid=tranid)
    return_url = url_for("admin_transactions")
    return render_template("verify.html", title="Bevestigen", message=message, transaction=transaction,
                           agree_url=agree_url, return_url=return_url), 200


@app.route('/admin/transactions/delete/<int:tranid>/exec')
def admin_transactions_delete_exec(tranid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    alert = (dbhandler.deltransaction(tranid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_transactions'))


@app.route('/admin/drinks', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks', 'Productbeheer', order=2)
def admin_drinks():
    form = DrinkForm()
    filters = ProductFilterForm()

    query = Product.query
    query = apply_filters(query)
    products = query.order_by(Product.order.asc()).all()

    if request.method == "POST":
        if form.validate_on_submit():
            alert = (
                dbhandler.adddrink(form.name.data, float(form.price.data), form.category.data, int(form.pos.data) + 1,
                                   form.image.data, form.hoverimage.data, form.recipe.data, form.inventory_warning.data,
                                   float(form.alcohol.data), form.volume.data, form.unit.data))
            flash(alert[0], alert[1])

            socket.update_stats()

            return redirect(url_for('admin_drinks'))
        else:
            flash(form.errors, "danger")
    flash_form_errors(form.errors)
    return render_template('admin/mandrinks.html', title="Productbeheer", h1="Productbeheer", Product=Product,
                           products=products, form=form, filters=filters), 200


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
        alert = (dbhandler.editdrink_attr(drinkid, form.name.data, float(form.price.data),
                                          form.category.data, int(form.pos.data) + 1,
                                          form.purchaseable.data, form.recipe.data, int(form.inventory_warning.data),
                                          float(form.alcohol.data), int(form.volume.data), form.unit.data))
        flash(alert[0], alert[1])

        socket.update_stats()

        return redirect(url_for('admin_drinks'))
    if form2.submit2.data and form2.validate_on_submit():
        alert = (dbhandler.editdrink_image(drinkid, form2.image.data, form2.hoverimage.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    flash_form_errors(form.errors)
    flash_form_errors(form2.errors)
    return render_template('admin/editdrink.html', title="{} bewerken".format(product.name),
                           h1="Pas {} (ID: {}) aan".format(product.name, product.id), product=product, form=form,
                           form2=form2, recipe=recipe[:-2]), 200


@app.route('/admin/drinks/delete/<int:drinkid>')
def admin_drinks_delete(drinkid):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    alert = (dbhandler.deldrink(drinkid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_drinks'))


@app.route('/admin/usergroups', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.usergroups', 'Groepenbeheer', order=2)
def admin_usergroups():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = UserGroupRegistrationForm()
    if form.validate_on_submit():
        alert = (dbhandler.addusergroup(form.name.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_usergroups'))
    flash_form_errors(form.errors)
    return render_template("admin/manusergroups.html", title="Groepen", h1="Groepenbeheer", form=form,
                           Usergroup=Usergroup), 200


@register_breadcrumb(app, '.admin.usergroups.confirm', 'Bevestigen', order=2)
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
    alert = (dbhandler.delusergroup(usergroupid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_usergroups'))


@register_breadcrumb(app, '.admin.inventory', 'Inventarisbeheer', order=2)
@app.route('/admin/inventory/', methods=['GET', 'POST'])
def admin_inventory():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = AddInventoryForm()
    if form.validate_on_submit():
        alert = (dbhandler.add_inventory(int(form.product.data), form.quantity.data,
                                         float(form.purchase_price.data), form.note.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_inventory'))

    flash_form_errors(form.errors)
    return render_template("admin/maninventory.html", title="Inventarisbeheer", h1="Inventarisbeheer",
                           backurl=url_for('index'), Product=Product,
                           Inventory=Inventory, form=form), 200


@register_breadcrumb(app, '.admin.inventorycorrect', 'Inventariscorrectie', order=2)
@app.route('/admin/inventory/correct', methods=['GET', 'POST'])
def admin_correct_inventory():
    products = [p.serialize for p in Product.query.filter(Product.recipe_input == None).all()]
    for p in products:
        p['stock'] = dbhandler.calcStock(p['id'])

    if request.method == 'POST':
        result = dbhandler.correct_inventory(request.get_json())
        if type(result) is tuple:
            flash(result[0], result[1])
        return redirect(url_for('admin'), code=302)

    inventories = [i.serialize for i in Inventory.query.filter(Inventory.quantity != 0).all()]
    usergroup_ids = {g.id: g.name for g in Usergroup.query.all()}
    return render_template("admin/inventorycorrection.html", title="Inventaris correctie", h1="Inventaris correctie",
                           Product=Product, products=products, Usergroup=Usergroup, inventories=inventories,
                           usergroup_ids=usergroup_ids)


@app.route('/admin/upgrade', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.upgrade', 'Opwaarderen', order=2)
def upgrade():
    if request.remote_addr != "127.0.0.1":
        abort(403)

    # Create the two forms that will be included
    upgr_form = UpgradeBalanceForm()
    decl_form = DeclarationForm()

    # If one of the forms has been submitted
    if (upgr_form.upgr_submit.data and upgr_form.validate_on_submit()) or \
            (decl_form.decl_submit.data and decl_form.validate_on_submit()):
        # Change the decimal amount to a float
        amount = float(upgr_form.amount.data)

        # The amount cannot be negative!
        if amount < 0.0:
            flash("Opwaardering kan niet negatief zijn!", "danger")
            return render_template('admin/upgrade.html', title='Opwaarderen', h1="Opwaarderen",
                                   upgr_form=upgr_form, decl_form=decl_form)

        # If the upgrade form has been filled in...
        if upgr_form.upgr_submit.data and upgr_form.validate_on_submit():
            # Add the upgrade to the database
            upgrade = (dbhandler.addbalance(int(upgr_form.user.data), "Opwaardering", amount))
            # Get the user for the messages that now follow
            user = User.query.get(upgrade.user_id)

            socket.send_transaction("{} heeft opgewaardeerd met € {}"
                                    .format(user.name, str("%.2f" % upgrade.amount).replace(".", ",")))
            flash("Gebruiker {} heeft succesvol opgewaardeerd met € {}"
                  .format(user.name,str("%.2f" % upgrade.amount).replace(".", ",")), "success")

        # If the declaration form has been filled in
        else:
            # Add the upgrade to the database
            upgrade = (dbhandler.add_declaration(int(decl_form.user.data), decl_form.description.data,
                                                 amount, int(decl_form.payer.data)))
            # Get the user for the messages that now follow
            user = User.query.get(upgrade.user_id)

            socket.send_transaction("{} heeft € {} teruggekregen ({})"
                                    .format(user.name, str("%.2f" % upgrade.amount).replace(".", ","),
                                            upgrade.description))
            flash("Gebruiker {} heeft succesvol € {} teruggekregen voor: {}"
                  .format(user.name, str("%.2f" % upgrade.amount).replace(".", ","), upgrade.description), "success")

        # Update the daily stats
        socket.update_stats()

        return redirect(url_for('admin'))

    # Show errors if there are any
    flash_form_errors(upgr_form.errors)
    flash_form_errors(decl_form.errors)
    return render_template('admin/upgrade.html', title='Opwaarderen', h1="Opwaarderen",
                           upgr_form=upgr_form, decl_form=decl_form)


@register_breadcrumb(app, '.admin.profit', 'Winst uitkeren', order=2)
@app.route('/admin/profit', methods=['GET', 'POST'])
def payout_profit():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = PayOutProfitForm()
    if form.validate_on_submit():
        alert = dbhandler.payout_profit(int(form.usergroup.data), float(form.amount.data), form.verification.data)
        flash(alert[0], alert[1])
        return redirect(url_for('payout_profit'))
    flash_form_errors(form.errors)
    return render_template("admin/manprofit.html", title="Winst uitkeren", h1="Winst uitkeren", Usergroup=Usergroup,
                           form=form), 200


@register_breadcrumb(app, '.admin.borrelmode', "Borrel Modus", order=2)
@app.route('/admin/borrelmode', methods=['GET', 'POST'])
def borrel_mode():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    form = BorrelModeForm()
    if form.validate_on_submit():
        dbhandler.set_borrel_mode(form.products.data, form.user.data, form.amount.data)
        flash('Borrel modus succesvol aangezet!', "success")

    # Get general data if borrel mode is still enabled
    borrel_data = dbhandler.borrel_mode()
    # Construct a list of products
    if borrel_data is not None:
        product_string = ""
        # For every product, add its name to the string
        for p in dbhandler.borrel_mode_drinks:
            product_string += Product.query.get(p).name + ", "
        # If there are products...
        if len(product_string) > 0:
            # Remove the final comma and space from the string
            product_string = product_string[:-2]
        # Add this string to the borrel data object
        borrel_data['products'] = product_string
        # Add whether borrel mode is still enabled
        borrel_data['enabled'] = dbhandler.borrel_mode_enabled

    flash_form_errors(form.errors)
    return render_template('admin/borrelmode.html', title="Borrel Modus beheren", h1="Borrel modus", form=form,
                           borrel_data=borrel_data), 200


@app.route('/admin/borrelmode/disable', methods=['GET'])
def disable_borrel_mode():
    dbhandler.borrel_mode_enabled = False
    flash("Borrel mode uitgeschakeld", "success")
    return redirect(url_for('borrel_mode'))


@register_breadcrumb(app, '.admin.soundboard', 'Soundboard', order=2)
@app.route('/admin/soundboard', methods=['GET', 'POST'])
def admin_soundboard():
    form = SoundBoardForm()
    if form.validate_on_submit():
        dbhandler.add_sound(form.name.data, form.key.data, form.code.data, form.file.data)
        flash('Geluid {} succesvol toegevoegd'.format(form.name.data), 'success')

    flash_form_errors(form.errors)
    return render_template('admin/mansounds.html', title="Beheer soundboard", h1="Beheer soundboard", form=form,
                           Sound=Sound)


@register_breadcrumb(app, '.admin.soundboard.confirm', 'Bevestigen', order=3)
@app.route('/admin/soundboard/delete/<int:sound_id>')
def admin_soundboard_delete(sound_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    sound = Sound.query.get(sound_id)
    message = "geluid " + sound.name + " wilt verwijderen?"
    agree_url = url_for("admin_soundboard_delete_exec", sound_id=sound_id)
    return_url = url_for("admin_soundboard")
    return render_template("verify.html", title="Bevestigen", message=message, user=user, agree_url=agree_url,
                           return_url=return_url), 200


@app.route('/admin/soundboard/delete/<int:sound_id>/exec')
def admin_soundboard_delete_exec(sound_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)
    alert = (dbhandler.del_sound(sound_id))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_soundboard'))


@app.route('/admin/recalcmax')
def recalculate_max_stats():
    transactions = Transaction.query.all()
    begindate = datetime(year=2019, month=7, day=1, hour=12, minute=0, second=0)
    for t in transactions:
        begindate2 = stats.get_yesterday_for_today(t.timestamp)
        if begindate2 != begindate:
            begindate = begindate2
            stats.reset_daily_stats()
        stats.update_daily_stats("euros", t.balchange)

        if t.purchase_id is not None:
            p = Purchase.query.get(t.purchase_id)
            if p.round:
                stats.update_daily_stats("rounds", 1)
            stats.update_daily_stats_drinker(p.user_id)
            if p.price > 0:
                stats.update_daily_stats_product(p.product_id, p.amount)
            stats.update_daily_stats("purchases", 1)
    stats.update_daily_stats("products", Product.query.filter(Product.purchaseable == True).count())
    stats.update_daily_stats("users", User.query.count())
    socket.update_stats()
    return redirect(url_for("index"))


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
    dbhandler.force_edit()
    return "succes"


##
#
# Statistieken
#
##


def getStatValue(elem):
    return elem[2]


@register_breadcrumb(app, '.stats', 'Statistieken', order=1)
@register_breadcrumb(app, '.stats.drink', 'Producten', order=2)
@register_breadcrumb(app, '.stats.user', 'Gebruikers', order=2)
@register_breadcrumb(app, '.stats.group', 'Groepen', order=2)
@app.route('/stats')
def stats_home():
    return render_template('stats/stats.html', title='Statistieken', h1='Statistieken', Product=Product, User=User)


@app.route('/stats/user/<int:userid>')
def stats_user_redirect(userid):
    return redirect(url_for('stats_user', userid=userid, begindate=app.config['STATS_BEGINDATE'],
                            enddate=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")))


@register_breadcrumb(app, '.stats.user.id', '', dynamic_list_constructor=view_user_dlc, order=3)
@app.route('/stats/user/<int:userid>/<string:begindate>/<string:enddate>')
def stats_user(userid, begindate, enddate):
    user = User.query.get(userid)
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")

    datat, idw, labelw, valuew = stats.balance_over_time_user(userid, parsedbegin, parsedend)
    ids, values, labels = stats.most_bought_products_per_user(userid, parsedbegin, parsedend)

    return render_template("stats/statsuser.html", title="Statistieken van " + user.name,
                           h1="Statistieken van " + user.name, ids=ids, data=values, labels=labels, idw=idw,
                           labelw=labelw, valuew=valuew,
                           datat=datat, lefturl="", righturl="", begindate=begindate, enddate=enddate), 200


def view_stats_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('stats_drink_redirect', drinkid=drink_id)}]


@app.route('/stats/drink/<int:drinkid>')
def stats_drink_redirect(drinkid):
    return redirect(url_for('stats_drink', drinkid=drinkid, begindate=app.config['STATS_BEGINDATE'],
                            enddate=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")))


@register_breadcrumb(app, '.stats.drink.id', '', dynamic_list_constructor=view_stats_drink_dlc, order=3)
@app.route('/stats/drink/<int:drinkid>/<string:begindate>/<string:enddate>')
def stats_drink(drinkid, begindate, enddate):
    product = Product.query.get(drinkid)
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")

    idsg, valuesg, labelsg = stats.most_bought_of_one_product_by_groups(drinkid, parsedbegin, parsedend)
    idsu, valuesu, labelsu = stats.most_bought_of_one_product_by_users(drinkid, parsedbegin, parsedend)

    return render_template("stats/statsproduct.html", title='Statistieken over {}'.format(product.name),
                           h1='Statistieken over {}'.format(product.name),
                           begindate=begindate, enddate=enddate, idsu=idsu, valuesu=valuesu, labelsu=labelsu, idsg=idsg,
                           valuesg=valuesg, labelsg=labelsg,
                           lefturl="", righturl=url_for("stats_drink_group_redirect", drinkid=drinkid, groupid=0)), 200


def view_stats_drink_group_dlc(*args, **kwargs):
    group_id = request.view_args['groupid']
    usergroup = Usergroup.query.get(group_id)
    return [{'text': usergroup.name,
             'url': url_for('stats_drink_group_redirect', drinkid=request.view_args['drinkid'], groupid=group_id)}]


@app.route('/stats/drink/<int:drinkid>/group/<int:groupid>')
def stats_drink_group_redirect(drinkid, groupid):
    return redirect(
        url_for('stats_drink_group', drinkid=drinkid, groupid=groupid, begindate=app.config['STATS_BEGINDATE'],
                enddate=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")))


@register_breadcrumb(app, '.stats.drink.id.group', '', dynamic_list_constructor=view_stats_drink_group_dlc, order=3)
@app.route('/stats/drink/<int:drinkid>/group/<int:groupid>/<string:begindate>/<string:enddate>')
def stats_drink_group(drinkid, groupid, begindate, enddate):
    product = Product.query.get(drinkid)
    usergroup = Usergroup.query.get(groupid)
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")

    idsu, valuesu, labelsu = stats.most_bought_of_one_product_by_users_from_group(drinkid, groupid, parsedbegin,
                                                                                  parsedend)
    idsg, valuesg, labelsg = stats.most_bought_of_one_product_by_groups_from_group(drinkid, groupid, parsedbegin,
                                                                                   parsedend)

    return render_template("stats/statsproduct.html",
                           title='Statistieken over {} voor {}'.format(product.name, usergroup.name),
                           h1='Statistieken over {} voor {}'.format(product.name, usergroup.name),
                           begindate=begindate, enddate=enddate, idsu=idsu, valuesu=valuesu, labelsu=labelsu, idsg=idsg,
                           valuesg=valuesg, labelsg=labelsg,
                           lefturl="", righturl=""), 200


@app.route('/test/exception')
def throw_exception():
    raise Exception


@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    if request.remote_addr != "127.0.0.1":
        abort(403)
    if request.args.get('emails') == 'True':
        if dbhandler.overview_emails:
            emailhandler.send_overview_emails()
        elif dbhandler.debt_emails:
            emailhandler.send_debt_emails()
    shutdown_server()
    app.logger.info('Tikker shutting down')
    return render_template('error.html', title="Tikker wordt afgesloten...", h1="Uitschakelen",
                           message="Tikker wordt nu afgesloten. Je kan dit venster sluiten.", gif_url="")


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
    dbhandler.rollback()
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


@register_breadcrumb(app, '.admin.bigscreen', 'BigScreen', order=2)
@app.route("/admin/bigscreen", methods=['GET', 'POST'])
def bigscreen():
    form_quote = AddQuoteForm()
    form_interrupt = SlideInterruptForm()
    form_spotify = ChooseSpotifyUser()

    if len(dbhandler.biertje_kwartiertje_participants) > 0:
        bk = {'playing': True,
              'participants': [User.query.get(x['user_id']) for x in dbhandler.biertje_kwartiertje_participants],
              'drink': Product.query.get(dbhandler.biertje_kwartiertje_drink).name,
              'playtime': dbhandler.biertje_kwartiertje_time}
    else:
        bk = {'playing': False}

    if form_quote.submit_quote.data and form_quote.validate_on_submit():
        alert = dbhandler.addquote(form_quote.quote.data, form_quote.author.data)
        flash(alert[0], alert[1])

        return redirect(url_for('bigscreen'))
    if form_interrupt.submit_interrupt.data and form_interrupt.validate_on_submit():
        socket.send_interrupt({"name": "Message", "data": form_interrupt.interrupt.data})

        return redirect(url_for('bigscreen'))

    if form_spotify.spotify_submit.data and form_spotify.validate_on_submit():
        if form_spotify.spotify_user.data != '0':
            spotify.set_cache(os.path.join(app.config['SPOTIFY_CACHE_FOLDER'],
                                           '.spotifyoauthcache-' + form_spotify.spotify_user.data))
            return redirect(url_for('api_spotify_login'))
        elif form_spotify.spotify_user.data == "0" and form_spotify.spotify_user_name.data != "":
            spotify.set_cache(os.path.join(app.config['SPOTIFY_CACHE_FOLDER'],
                                           '.spotifyoauthcache-' + form_spotify.spotify_user_name.data))
            return redirect(url_for('api_spotify_login'))

    return render_template('admin/bigscreen.html', title="BigScreen Beheer", h1="BigScreen Beheer",
                           form_quote=form_quote, bk=bk,
                           form_interrupt=form_interrupt, form_spotify=form_spotify,
                           spusername=spotify.current_user), 200


@register_breadcrumb(app, '.admin.bigscreen.quotes', 'Quotes', order=3)
@app.route('/admin/bigscreen/quotes', methods=['GET'])
def admin_quotes():
    if request.remote_addr != "127.0.0.1":
        abort(403)

    if 'all' in request.args:
        quotes = Quote.query.all()
        all_quotes = True
    else:
        quotes = Quote.query.filter(Quote.approved == False).all()
        all_quotes = False

    return render_template('admin/manquotes.html', title="Citaatbeheer", h1="Citaatbeheer", quotes=quotes,
                           all_quotes=all_quotes)


@register_breadcrumb(app, '.admin.bigscreen.quotes.confirm', 'Bevestigen', order=4)
@app.route('/admin/bigscreen/quotes/delete/<int:q_id>')
def admin_quotes_delete(q_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)

    q = Quote.query.get(q_id)
    message = 'quote met ID {} ({}) door {}'.format(str(q.id), q.value, q.author)
    agree_url = url_for('admin_quotes_delete_exec', q_id=q_id)
    return_url = url_for('admin_quotes')
    return render_template('verify.html', title='Bevestigen', message=message, agree_url=agree_url,
                           return_url=return_url)


@app.route('/admin/bigscreen/quotes/delete/<int:q_id>/exec')
def admin_quotes_delete_exec(q_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)

    alert = dbhandler.del_quote(q_id)
    flash(alert[0], alert[1])
    return redirect(url_for('admin_quotes'))


@app.route('/admin/bigscreen/quotes/approve/<int:q_id>')
def admin_quotes_approve(q_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)

    alert = dbhandler.approve_quote(q_id)
    flash(alert[0], alert[1])
    return redirect(url_for('admin_quotes'))


@register_breadcrumb(app, '.admin.bigscreen.bk', 'Biertje Kwartiertje', order=3)
@app.route("/admin/bigscreen/biertjekwartiertje")
def biertje_kwartiertje():
    usergroups = get_usergroups_with_users()
    dinnerid = dbhandler.settings['dinner_product_id']
    products = Product.query.filter(and_(Product.purchaseable == True, Product.id != dinnerid)).all()

    drink = Product.query.get(1)

    already_playing = []
    for i in dbhandler.biertje_kwartiertje_participants:
        for j in range(0, i['amount']):
            already_playing.append({'id': i['user_id'], 'name': User.query.get(i['user_id']).name})

    if len(dbhandler.biertje_kwartiertje_participants) > 0:
        playtime = dbhandler.biertje_kwartiertje_time
    else:
        playtime = 15

    return render_template('admin/biertjekwartiertje.html', title="Biertje Kwartiertje",
                           h1="Biertje kwartiertje instellen", drink=drink, usergroups=usergroups, shared=False,
                           User=User, products=products, already_playing=already_playing, playtime=playtime), 200


@app.route("/admin/bigscreen/biertjekwartiertje/<cart_string>")
def start_biertje_kwartiertje(cart_string):
    old_participants = dbhandler.biertje_kwartiertje_participants
    parsed_cart = cart.parse_cart_string(cart_string, -1)
    dbhandler.biertje_kwartiertje_participants = parsed_cart['orders']

    if len(dbhandler.biertje_kwartiertje_participants) > 0:
        dbhandler.biertje_kwartiertje_time = int(request.args['time'])
        dbhandler.biertje_kwartiertje_drink = int(request.args['drink'])
        # If biertje kwartiertje has not started yet, we need to update it on BigScreen
        if len(old_participants) == 0:
            # Start biertje kwartiertje (aka update it with the time)
            socket.update_biertje_kwartiertje()
    else:
        stop_biertje_kwartiertje()

    return redirect(url_for("bigscreen"))


@app.route("/admin/bigscreen/biertjekwartiertje/stop")
def stop_biertje_kwartiertje():
    dbhandler.biertje_kwartiertje_participants = []
    dbhandler.biertje_kwartiertje_time = 0
    dbhandler.biertje_kwartiertje_drink = -1
    socket.stop_biertje_kwartiertje()
    return redirect(url_for("bigscreen"))


@app.route("/admin/bigscreen/biertjekwartiertje/update")
def update_biertje_kwartiertje():
    socket.update_biertje_kwartiertje()
    return redirect(url_for("bigscreen"))


@app.route("/api/spotify/login")
def api_spotify_login():
    return spotify.login(request)


@app.route('/api/spotify/logout')
def api_spotify_logout():
    current_user = spotify.current_user
    spotify.logout()
    flash("Spotify gebruiker {} uitgelogd".format(current_user), "success")
    return redirect(url_for('bigscreen'))


@app.route('/api/spotify/covers/<string:id>')
def api_spotify_get_album_cover(id):
    return render_template(url_for('.static', filename='covers/{}.jpg'.format(id)))


@app.route('/api/spotify/currently_playing')
def api_spotify_currently_playing():
    return jsonify(spotify.current_playback())


@app.route('/api/spotify/me')
def api_spotify_user():
    return jsonify(spotify.me())


@app.route('/api/total_alcohol')
def api_total_alcohol():
    begindate = "2019-09-01"
    enddate = "2019-12-31"
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")

    ids, values, labels = stats.most_alcohol_drank_by_users(parsedbegin, parsedend)

    return jsonify({"ids": ids,
                    "values": values,
                    "labels": labels})


@app.route('/api/bigscreen/snow')
def api_disable_snow():
    socket.disable_snow()
    return redirect(url_for('bigscreen'))


@app.route('/api/bigscreen/reload')
def api_reload_bigscreen():
    socket.send_reload()
    return redirect(url_for('bigscreen'))
