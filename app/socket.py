import math

from app import app, socketio, stats, spotify, dbhandler, EN_SNOW
from flask_socketio import emit
from datetime import datetime
from sqlalchemy import and_
from random import randrange
from app.models import Product, Quote, User, Purchase
from urllib.error import URLError
from ics import Calendar
import pytz
import urllib.request
import copy

most_drank = 0
second_most_drank = 0
third_most_drank = 0
slide_time = 0

cal = Calendar()


@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


@socketio.on('init', namespace='/test')
def init_bigscreen(msg):
    global slide_time
    slide_time = msg['slide_time']
    slide_name = msg['slide_name']
    spotify_data = get_spotify_data()
    slide = get_slide_data(slide_name)
    stats_daily, stats_max = get_stats()
    emit('init', {'slide': {'name': slide_name,
                            'data': slide},
                  'spotify': spotify_data,
                  'stats': {'daily': stats_daily,
                            'max': stats_max},
                  'snow': EN_SNOW})


@socketio.on('spotify', namespace='/test')
def update_spotify_request():
    spotify_data = get_spotify_data()
    emit('spotify update', spotify_data)


@socketio.on('biertje_kwartiertje_exec', namespace='/test')
def biertje_kwartiertje_purchase():
    drink_id = dbhandler.biertje_kwartiertje_drink
    product = Product.query.get(drink_id)

    total_bought = 0
    success_messages = {}
    for participant in dbhandler.biertje_kwartiertje_participants:
        total_bought += int(participant[1])
        if dbhandler.borrel_mode_enabled and drink_id in dbhandler.borrel_mode_drinks:
            dbhandler.addpurchase(drink_id, int(participant[0]), int(participant[1]), False, 0)
        else:
            alert = (dbhandler.addpurchase(drink_id, int(participant[0]), int(participant[1]), False, product.price))
            success_messages = process_alert_from_adddrink(alert, success_messages)

    if dbhandler.borrel_mode_enabled and drink_id in dbhandler.borrel_mode_drinks:
        alert = (dbhandler.addpurchase(drink_id, int(dbhandler.settings['borrel_mode_user']), total_bought, True, product.price))
        success_messages = process_alert_from_adddrink(alert, success_messages)

    final_flash = ""
    for front, end in success_messages.items():
        final_flash = final_flash + str(front) + " " + end + ", "
    if final_flash != "":
        send_transaction(final_flash[:-2])

    update_stats()


def process_alert_from_adddrink(alert, success_messages):
    if alert[3] == "success":
        q = alert[0]
        if math.floor(q) == q:
            q = math.floor(q)
        key = "{}x {} voor".format(q, alert[1])
        if key not in success_messages:
            success_messages[key] = alert[2]
        else:
            success_messages[key] = success_messages[key] + ", {}".format(alert[2])
    return success_messages


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
    global third_most_drank, second_most_drank, most_drank, cal

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
        products = Product.query.filter(
            and_(Product.purchaseable == True, Product.id != dbhandler.settings['dinner_product_id'])).order_by(
            Product.order.asc()).all()
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

            idsb, valuesb, namesb = stats.most_bought_of_one_product_by_users(dbhandler.settings['beer_product_id'],
                                                                              begindate, enddate)
            idsf, valuesf, namesf = stats.most_bought_of_one_product_by_users(dbhandler.settings['flugel_product_id'],
                                                                              begindate, enddate)

            most_beers = get_top_users(namesb, valuesb)
            most_flugel = get_top_users(namesf, valuesf)

            return {'beer': most_beers,
                    'flugel': most_flugel}

    elif name == "RecentlyPlayed":
        history = []

        now = datetime.now()
        for i in range(1, len(spotify.history)):
            timediff = now - spotify.history[i]['end-time']
            minutes = int((timediff.seconds + slide_time) / 60)
            seconds = int((timediff.seconds + slide_time) % 60)
            if minutes >= 10:
                minutes = str(minutes)
            else:
                minutes = "0" + str(minutes)
            if seconds >= 10:
                seconds = str(seconds)
            else:
                seconds = "0" + str(seconds)
            history.append({"timestamp": "{}:{}".format(minutes, seconds),
                            "title": spotify.history[i]['title'],
                            "artist": spotify.history[i]['artist']})

        return history

    elif name == "Calendar":
        get_current_calendar()
        now = pytz.utc.localize(datetime.now())

        items = []
        for event in cal.events:
            if now > event.begin.datetime:
                continue
            diff = event.begin.datetime.date() - now.date()
            items.append({'name': event.name,
                          'datetime': event.begin.datetime.date(),
                          'date': event.begin.datetime.strftime("%d/%m/%Y %H:%M"),
                          'days': diff.days})

        items = sorted(items, key=lambda k: k['datetime'])
        for i in items:
            del i['datetime']

        if len(items) == 0:
            return {'upcoming_events': False}
        if len(items) > 10:
            items = items[0:10]

        return {'upcoming_events': True,
                'calendar': items}

    return {}


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


def start_biertje_kwartiertje():
    socketio.emit('biertje_kwartiertje_start', {'minutes': dbhandler.biertje_kwartiertje_time}, namespace='/test')


def stop_biertje_kwartiertje():
    socketio.emit('biertje_kwartiertje_stop', None, namespace='/test')


def get_current_calendar():
    global cal
    req = urllib.request.Request('https://drive.kvls.nl/remote.php/dav/public-calendars/BKWDW9PJT2mmoRa4?export')
    try:
        response = urllib.request.urlopen(req)
    except URLError:
        return
    cal = Calendar(response.read().decode('iso-8859-1'))


def get_top_users(names, values):
    if len(names) > 0:
        most = names[0]
        for i in range(1, len(names)):
            if values[i - 1] == values[i]:
                most += ", " + names[i]
            else:
                break
        return most
    return "Niemand :("
