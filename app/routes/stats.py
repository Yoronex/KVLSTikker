from datetime import datetime, timedelta
from flask_breadcrumbs import register_breadcrumb

from app.routes import *
from app import statshandler

plotcolours = ["#0b8337", "#ffd94a", "#707070"]


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


def view_user_dlc(*args, **kwargs):
    user_id = request.view_args['userid']
    user = User.query.get(user_id)
    return [{'text': user.name, 'url': url_for('user', userid=user_id)}]


@register_breadcrumb(app, '.stats.user.id', '', dynamic_list_constructor=view_user_dlc, order=3)
@app.route('/stats/user/<int:userid>/<string:begindate>/<string:enddate>')
def stats_user(userid, begindate, enddate):
    user = User.query.get(userid)
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")

    datat, idw, labelw, valuew = statshandler.balance_over_time_user(userid, parsedbegin, parsedend)
    ids, values, labels = statshandler.most_bought_products_per_user(userid, parsedbegin, parsedend)

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

    idsg, valuesg, labelsg = statshandler.most_bought_of_one_product_by_groups(drinkid, parsedbegin, parsedend)
    idsu, valuesu, labelsu = statshandler.most_bought_of_one_product_by_users(drinkid, parsedbegin, parsedend)

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

    idsu, valuesu, labelsu = statshandler.most_bought_of_one_product_by_users_from_group(drinkid, groupid, parsedbegin,
                                                                                  parsedend)
    idsg, valuesg, labelsg = statshandler.most_bought_of_one_product_by_groups_from_group(drinkid, groupid, parsedbegin,
                                                                                   parsedend)

    return render_template("stats/statsproduct.html",
                           title='Statistieken over {} voor {}'.format(product.name, usergroup.name),
                           h1='Statistieken over {} voor {}'.format(product.name, usergroup.name),
                           begindate=begindate, enddate=enddate, idsu=idsu, valuesu=valuesu, labelsu=labelsu, idsg=idsg,
                           valuesg=valuesg, labelsg=labelsg,
                           lefturl="", righturl=""), 200
