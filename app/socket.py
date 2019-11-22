from app import app, socketio, stats, spotify, dbhandler
from flask_socketio import emit
from datetime import datetime
from sqlalchemy import and_
from random import randrange
from app.models import Product, Quote, User

import copy

@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


@socketio.on('init', namespace='/test')
def init_bigscreen(msg):
    print(msg)
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
        return {'data': spotify.current_playback(), 'logged in': True}
    else:
        return {'logged in': False}



@socketio.on('slide_data', namespace='/test')
def update_slide_data(msg):
    name = msg["name"]
    emit('slide_data', {"name": name,
                        "data": get_slide_data(name)})


def get_slide_data(name):
    if name == "DrankTonight":
        data = stats.most_bought_products_by_users_today(datetime.now())
        return {'labels': data[2],
                'values': data[1]}

    elif name == "PriceList":
        pnames = []
        prices = []
        products = Product.query.filter(and_(Product.purchaseable == True)).order_by(Product.order.asc()).all()
        for p in products:
            pnames.append(p.name)
            prices.append("€ {}".format(('%.2f' % p.price).replace('.', ',')))
        return {"names": pnames,
                "prices": prices}

    elif name == "Quote":
        quotes = Quote.query.all()
        q = quotes[randrange(len(quotes))]
        emit('slide_data', {"name": name,
                            "data": q.value})
    elif name == "Debt":
        unames = []
        udebt = []
        users = User.query.filter(User.balance < 0).order_by(User.balance.asc()).all()
        for u in users:
            unames.append(u.name)
            udebt.append("€ {}".format(('%.2f' % u.balance).replace('.', ',')))
        return {'names': unames,
                'amount': udebt}

    return {}


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
