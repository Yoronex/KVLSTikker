from app import app, socketio, stats, spotify, dbhandler
from flask_socketio import emit
from datetime import datetime
from sqlalchemy import and_
from random import randrange
from app.models import Product, Quote, User, Purchase

import copy

most_drank = 0
second_most_drank = 0
third_most_drank = 0


@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


@socketio.on('init', namespace='/test')
def init_bigscreen(msg):
    slide_name = msg['slide_name']
    slide = get_slide_data(slide_name)
    spotify_data = get_spotify_data()
    stats_daily, stats_max = get_stats()
    emit('init', {'slide': {'name': slide_name,
                            'data': slide},
                  'spotify': spotify_data,
                  'stats': {'daily': stats_daily,
                            'max': stats_max}})


@socketio.on('spotify', namespace='/test')
def update_spotify_request():
    spotify_data = get_spotify_data()
    emit('spotify update', spotify_data)


def get_spotify_data():
    if spotify.sp is not None:
        return {'data': spotify.current_playback(), 'logged in': True, "user": spotify.current_user}
    else:
        return {'logged in': False}



@socketio.on('slide_data', namespace='/test')
def update_slide_data(msg):
    name = msg["name"]
    emit('slide_data', {"name": name,
                        "data": get_slide_data(name)})


def get_slide_data(name):
    global third_most_drank, second_most_drank, most_drank

    if name == "DrankTonight":
        data = stats.most_bought_products_by_users_today(datetime.now())
        if len(data[0]) >= 3:
            third_most_drank = data[0][2]
        if len(data[0]) >= 2:
            second_most_drank = data[0][1]
        if len(data[0]) >= 1:
            most_drank = data[0][0]

        return {'labels': data[2],
                'values': data[1]}

    if name == "MostDrank1":
        return most_drank_data(most_drank)

    if name == "MostDrank2":
        return most_drank_data(second_most_drank)

    if name == "MostDrank3":
        return most_drank_data(third_most_drank)

    elif name == "PriceList":
        pnames = []
        prices = []
        products = Product.query.filter(and_(Product.purchaseable == True, Product.id != dbhandler.settings['dinner_product_id'])).order_by(Product.order.asc()).all()
        for p in products:
            pnames.append(p.name)
            prices.append("€ {}".format(('%.2f' % p.price).replace('.', ',')))
        return {"names": pnames,
                "prices": prices}

    elif name == "Quote":
        quotes = Quote.query.all()
        q = quotes[randrange(len(quotes))]
        return q.value

    elif name == "Debt":
        unames = []
        udebt = []
        users = User.query.filter(User.balance < 0).order_by(User.balance.asc()).all()
        for u in users:
            unames.append(u.name)
            udebt.append("€ {}".format(('%.2f' % u.balance).replace('.', ',')))
        return {'names': unames,
                'amount': udebt}

    elif name == "Title":
        if dbhandler.settings['beer_product_id'] is not None and dbhandler.settings['flugel_product_id'] is not None:
            enddate = datetime.now()
            begindate = stats.get_yesterday_for_today(enddate)

            idsb, valuesb, namesb = stats.most_bought_of_one_product_by_users(dbhandler.settings['beer_product_id'], begindate, enddate)
            idsf, valuesf, namesf = stats.most_bought_of_one_product_by_users(dbhandler.settings['flugel_product_id'], begindate, enddate)

            if len(namesb) > 0:
                most_beers = namesb[0]
                for i in range(1, len(namesb)):
                    if valuesb[i - 1] == valuesb[i]:
                        most_beers += ", " + namesb[i]
                    else:
                        break
            else:
                most_beers = "Niemand :("

            if len(namesf) > 0:
                most_flugel = namesf[0]
                for i in range(1, len(namesf)):
                    if valuesf[i - 1] == valuesf[i]:
                        most_flugel += ", " + namesf[i]
                    else:
                        break
            else:
                most_flugel = "Niemand :("

                return {'beer': most_beers,
                        'flugel': most_flugel}
    elif name == "RecentlyPlayed":
        history = []

        now = datetime.now()
        for i in range(1, len(spotify.history)):
            timediff = now - spotify.history[i]['end-time']
            history.append({"timestamp": "- {0:0=2d}:{0:0=2d}".format(int(timediff.seconds / 3600), int(timediff.seconds / 60)),
                            "title": spotify.history[i]['title'],
                            "artist": spotify.history[i]['artist']})

        return history

    return


def most_drank_data(drinkid):
    if drinkid > 0:
        data = stats.most_bought_of_one_product_by_users_today(drinkid, datetime.now())
        return {'labels': data[2],
                'values': data[1],
                'product_name': Product.query.get(drinkid).name}
    else:
        return {'labels': [],
                'values': [],
                'product_name': ""}


def update_stats():
    daily, maxim = get_stats()
    socketio.emit('stats', {"daily": daily, "max": maxim}, namespace='/test')


def get_stats():
    daily = copy.deepcopy(stats.daily_stats)
    maxim = copy.deepcopy(stats.max_stats)

    for key, val in daily.items():
        if key != "euros":
            daily[key] = int(val)
    for key, val in maxim.items():
        if key != "max-stats-euros":
            maxim[key] = int(val)
    daily["euros"] = "€ {}".format(('%.2f' % daily["euros"]).replace('.', ','))
    maxim["max-stats-euros"] = "€ {}".format(('%.2f' % maxim["max-stats-euros"]).replace('.', ','))

    return daily, maxim


def send_interrupt(message):
    socketio.emit('slide_interrupt', {'message': message}, namespace='/test')


def send_transaction(message):
    socketio.emit('transaction', {"name": "Transaction", "message": message}, namespace='/test')


def send_reload():
    socketio.emit('reload', None, namespace='/test')


def disable_snow():
    socketio.emit('snow', None, namespace='/test')
