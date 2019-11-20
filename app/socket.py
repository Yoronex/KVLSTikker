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


@socketio.on('spotify', namespace='/test')
def update_spotify_request():
    if spotify.sp is not None:
        emit('spotify update', {'data': spotify.current_playback(), 'logged in': True})
    else:
        emit('spotify update', {'logged in': False})


@socketio.on('slide_data', namespace='/test')
def update_slide_data(msg):
    name = msg["name"]

    if name == "DrankTonight":
        data = stats.most_bought_products_by_users_today(datetime.now())
        emit('slide_data', {"name": name,
                            "data": {"labels": data[2],
                                     "values": data[1]}
                            })
        return
    elif name == "PriceList":
        pnames = []
        prices = []
        products = Product.query.filter(and_(Product.purchaseable == True)).order_by(Product.order.asc()).all()
        for p in products:
            pnames.append(p.name)
            prices.append("€ {}".format(('%.2f' % p.price).replace('.', ',')))
        emit('slide_data', {"name": name,
                            "data": {"names": pnames,
                                     "prices": prices}
                            })
        return
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
        emit('slide_data', {'name': name,
                            "data": {"names": unames,
                                     "amount": udebt}})


def update_stats():
    daily = copy.deepcopy(stats.daily_stats)
    max = copy.deepcopy(stats.max_stats)

    for key, val in daily.items():
        if key != "euros":
            daily[key] = int(val)
    for key, val in max.items():
        if key != "max-stats-euros":
            max[key] = int(val)
    daily["euros"] = "€ {}".format(('%.2f' % daily["euros"]).replace('.', ','))
    max["max-stats-euros"] = "€ {}".format(('%.2f' % max["max-stats-euros"]).replace('.', ','))

    socketio.emit('stats', {"daily": daily, "max": max}, namespace='/test')


def send_interrupt(message):
    socketio.emit('slide_interrupt', {'message': message}, namespace='/test')


def send_transaction(message):
    socketio.emit('transaction', {"name": "Transaction", "message": message}, namespace='/test')
