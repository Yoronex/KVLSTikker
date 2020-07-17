from app import app, socketio, statshandler, spotify, dbhandler, EN_SNOW, cart
from flask_socketio import emit
from datetime import datetime
from sqlalchemy import and_
from random import randrange
from app.models import Product, Quote, User
from urllib.error import URLError
from ics import Calendar
import pytz
import urllib.request
import copy

bigscreen_connected = False
last_updated_slide = ""
most_drank = 0
second_most_drank = 0
third_most_drank = 0
slide_time = 0

cal = Calendar()
last_calendar_update = datetime.strptime('1970-01-01', "%Y-%m-%d")


@socketio.on('connect', namespace='/bigscreen')
def connected():
    global bigscreen_connected
    app.logger.info('Tikker BigScreen connected')
    bigscreen_connected = True


@socketio.on('disconnect', namespace='/bigscreen')
def disconnected():
    global bigscreen_connected
    app.logger.info('Tikker BigScreen disconnected')
    bigscreen_connected = False


@socketio.on('init', namespace='/bigscreen')
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


@socketio.on('spotify', namespace='/bigscreen')
def update_spotify_request():
    spotify_data = get_spotify_data()
    emit('spotify update', spotify_data)


@socketio.on('biertje_kwartiertje_exec', namespace='/bigscreen')
def biertje_kwartiertje_purchase():
    update_biertje_kwartiertje()
    drink_id = dbhandler.biertje_kwartiertje_drink
    cart.purchase_from_orders(dbhandler.biertje_kwartiertje_participants, drink_id)


def get_spotify_data():
    if spotify.sp is not None:
        return {'data': spotify.current_playback(), 'logged in': True, "user": spotify.current_user}
    else:
        return {'logged in': False}


@socketio.on('slide_data', namespace='/bigscreen')
def update_slide_data(msg):
    global last_updated_slide
    name = msg["name"]
    app.logger.info("Received request to update slide {}".format(name))
    last_updated_slide = name
    emit('slide_data', {"name": name,
                        "data": get_slide_data(name)})
    app.logger.info("Sent slide update response for slide {}".format(name))


def get_slide_data(name):
    global third_most_drank, second_most_drank, most_drank, cal, last_calendar_update

    if name == "DrankTonight":
        data = statshandler.most_bought_products_by_users_today(datetime.now())
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
        quotes = Quote.query.filter(Quote.approved == True).all()
        q = quotes[randrange(len(quotes))]
        return q.value

    elif name == "Debt":
        unames = []
        udebt = []
        # Get all the users with a negative balance in order from low to high
        users = User.query.filter(User.balance < 0).order_by(User.balance.asc()).all()
        # Loop over all these users
        for u in users:
            # Add their name and their balance to the list
            unames.append(u.name)
            udebt.append("€ {}".format(('%.2f' % u.balance).replace('.', ',')))
        return {'names': unames,
                'amount': udebt}

    elif name == "TopBalance":
        unames = []
        ubalances = []
        # Get all the users with a positive balance in order from high to low
        users = User.query.filter(User.balance > 0).order_by(User.balance.desc()).all()
        for u in users:
            unames.append(u.name)
            ubalances.append("€ {}".format(('%.2f' % u.balance).replace('.', ',')))
        return {'names': unames,
                'amount': ubalances}

    elif name == "Balance":
        unames = []
        ubalances = []
        unparsed = []
        # Loop over all users that are seen today
        for id in statshandler.daily_stats_seen_users:
            # Get the user object
            u = User.query.get(id)
            # Add this user with their name and balance to the list of users
            unames.append(u.name)
            ubalances.append("€ {}".format(('%.2f' % u.balance).replace('.', ',')))
            unparsed.append(u.balance)
        return {'names': unames,
                'amount': ubalances,
                'unparsed': unparsed}

    elif name == "Title":
        if dbhandler.settings['beer_product_id'] is not None and dbhandler.settings['flugel_product_id'] is not None:
            enddate = datetime.now()
            begindate = statshandler.get_yesterday_for_today(enddate)

            idsb, valuesb, namesb = statshandler.most_bought_of_one_product_by_users(dbhandler.settings['beer_product_id'],
                                                                              begindate, enddate)
            idsf, valuesf, namesf = statshandler.most_bought_of_one_product_by_users(dbhandler.settings['flugel_product_id'],
                                                                              begindate, enddate)

            most_beers = get_top_users(namesb, valuesb)
            most_flugel = get_top_users(namesf, valuesf)

            return {'beer': most_beers,
                    'flugel': most_flugel}
        else:
            return {'beer': "Niemand :(",
                    'flugel': "Niemand :("}

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
        if (datetime.now() - last_calendar_update).seconds > app.config['CALENDAR_UPDATE_INTERVAL']:
            try:
                get_current_calendar()
                last_calendar_update = datetime.now()
            except URLError:
                return {}
        now = pytz.utc.localize(datetime.now())

        items = []
        for event in cal.events:
            if now > event.begin.datetime or (event.description is not None and "TIKKERIGNORE" in event.description):
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

    elif name == "Birthdays":
        upcoming_birthdays = dbhandler.upcoming_birthdays()
        result = []

        for u in upcoming_birthdays:
            result.append({'user': u['user'],
                           'age': u['age'],
                           'birthday': u['birthday'].strftime("%d/%m/%Y"),
                           'days': u['days']})
        return result[:10]

    return {}


def most_drank_data(drinkid):
    if drinkid > 0:
        data = statshandler.most_bought_of_one_product_by_users_today(drinkid, datetime.now())
        return {'labels': data[2],
                'values': data[1],
                'product_name': Product.query.get(drinkid).name}
    else:
        return {'labels': [],
                'values': [],
                'product_name': ""}


def update_stats():
    global last_updated_slide
    daily, maxim = get_stats()
    app.logger.info("Update stats and recent slide")
    socketio.emit('stats', {"daily": daily, "max": maxim}, namespace='/bigscreen')
    socketio.emit('slide_data', {"name": last_updated_slide,
                                 "data": get_slide_data(last_updated_slide)}, namespace='/bigscreen')
    app.logger.info("Finished updating stats and recent slide")


def get_stats():
    daily = copy.deepcopy(statshandler.daily_stats)
    maxim = copy.deepcopy(statshandler.max_stats)

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
    socketio.emit('slide_interrupt', {'message': message}, namespace='/bigscreen')


def send_transaction(message):
    socketio.emit('transaction', {"name": "Transaction", "message": message}, namespace='/bigscreen')


def send_reload():
    socketio.emit('reload', None, namespace='/bigscreen')


def disable_snow():
    socketio.emit('snow', None, namespace='/bigscreen')


def toggle_fireplace():
    socketio.emit('fireplace', None, namespace='/bigscreen')


def update_biertje_kwartiertje():
    socketio.emit('biertje_kwartiertje_start', {'minutes': dbhandler.biertje_kwartiertje_time}, namespace='/bigscreen')


def stop_biertje_kwartiertje():
    socketio.emit('biertje_kwartiertje_stop', None, namespace='/bigscreen')


def get_current_calendar():
    global cal
    req = urllib.request.Request(app.config['CALENDAR_URL'])
    response = urllib.request.urlopen(req)
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
