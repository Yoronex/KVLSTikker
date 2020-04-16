import copy

from flask import render_template, flash, redirect, url_for, request, make_response
from flask_breadcrumbs import register_breadcrumb

from app import stats, dbhandler, cart
from app.forms import *
from app.models import *
from app.routes import get_usergroups_with_users, apply_filters, calculate_pagination_with_basequery

birthday = False
showed_birthdays = True
birthdays = dbhandler.is_birthday()
if len(birthdays) > 0:
    birthday = True
    showed_birthdays = False


@app.route('/index')
@app.route('/drink')
@app.route('/')
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
