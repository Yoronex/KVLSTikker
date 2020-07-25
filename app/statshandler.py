from sqlalchemy import and_
from app import app, db, round_down, round_up, get_all_products_from_category
from app.models import *
from app.dbhandler import settings
from datetime import datetime, timedelta


daily_stats = {"products": 0,
               "users": 0,
               "drinkers": 0,
               "beers": 0,
               "mixes": 0,
               "shots": 0,
               "purchases": 0,
               "rounds": 0,
               "euros": 0.0}

daily_stats_seen_users = set({})

max_stats = {"max-stats-products": 0,
             "max-stats-users": 0,
             "max-stats-drinkers": 0,
             "max-stats-beers": 0,
             "max-stats-mixes": 0,
             "max-stats-shots": 0,
             "max-stats-purchases": 0,
             "max-stats-rounds": 0,
             "max-stats-euros": 0.0}


def getStatValue(elem):
    return elem[2]


def getIDnumber(elem):
    return elem[0]


def init_daily_stats():
    global daily_stats
    global daily_stats_seen_users

    enddate = datetime.now()
    begindate = get_yesterday_for_today(enddate)

    daily_stats["products"] = Product.query.filter(Product.purchaseable == True, Product.id != settings['dinner_product_id']).count()
    daily_stats["users"] = User.query.count()
    drinkers = Purchase.query.filter(Purchase.timestamp > begindate, Purchase.product_id != settings['dinner_product_id']).group_by(Purchase.user_id).all()
    for d in drinkers:
        daily_stats_seen_users.add(d.user_id)
    daily_stats["drinkers"] = len(drinkers)
    daily_stats["rounds"] = Purchase.query.filter(Purchase.timestamp > begindate, Purchase.round == True, Purchase.product_id != settings['dinner_product_id']).count()
    daily_stats["purchases"] = Purchase.query.filter(Purchase.timestamp > begindate, Purchase.product_id != settings['dinner_product_id'], Purchase.price > 0).count()

    purchases = Purchase.query.filter(Purchase.timestamp > begindate, Purchase.product_id != settings['dinner_product_id'], Purchase.price > 0).all()
    products = {}
    for p in purchases:
        if p.product_id not in products.keys():
            products[p.product_id] = Product.query.get(p.product_id).category
        category = products[p.product_id]

        if category == "Bieren":
            daily_stats["beers"] += p.amount
        elif category == "Mixjes":
            daily_stats["mixes"] += p.amount
        elif category == "Shots":
            daily_stats["shots"] += p.amount

    for u in Upgrade.query.all():
        daily_stats["euros"] += u.amount

    for p in Purchase.query.all():
        daily_stats["euros"] -= p.amount * p.price


def init_max_stats():
    global max_stats
    sses = Setting.query.all()
    settings_keys = []
    for s in sses:
        settings_keys.append(s.key)

    for k in max_stats.keys():
        if k not in settings_keys:
            s = Setting(key=k, value=0)
            db.session.add(s)
            db.session.commit()

    for s in Setting.query.all():
        if s.key in max_stats.keys():
            if s.key == "max-stats-euros":
                max_stats[s.key] = float(s.value)
            else:
                max_stats[s.key] = int(float(s.value))


def reset_daily_stats(full=False):
    global daily_stats
    global daily_stats_seen_users

    daily_stats["drinkers"] = 0
    daily_stats["beers"] = 0
    daily_stats["mixes"] = 0
    daily_stats["shots"] = 0
    daily_stats["purchases"] = 0
    daily_stats["rounds"] = 0
    daily_stats_seen_users = set({})

    if full:
        daily_stats["products"] = 0
        daily_stats["users"] = 0
        daily_stats["euros"] = 0


def reset_max_stats():
    for key in ['drinkers', 'beers', 'mixes', 'shots', 'purchases', 'rounds', 'euros', 'products', 'users']:
        real_key = 'max-stats-' + key
        max_stats[real_key] = 0
        setting = Setting.query.get(real_key)
        setting.value = str(0)
        db.session.commit()


def update_daily_stats(key, update_val):
    daily_stats[key] += update_val
    if daily_stats[key] > max_stats["max-stats-" + key]:
        max_stats["max-stats-" + key] = daily_stats[key]
        setting = Setting.query.get("max-stats-" + key)
        setting.value = str(daily_stats[key])
        db.session.commit()


def update_daily_stats_product(drinkid, amount):
    category = Product.query.get(drinkid).category
    if category == "Bieren":
        update_daily_stats("beers", amount)
    elif category == "Mixjes":
        update_daily_stats("mixes", amount)
    elif category == "Shots":
        update_daily_stats("shots", amount)


def update_daily_stats_drinker(user_id):
    global daily_stats_seen_users
    # Get the old length of the seen users
    old_length = len(daily_stats_seen_users)
    # Add the user to the set of seen users
    daily_stats_seen_users.add(user_id)
    # Get the new length of the seen users (can be one larger or equal to the old size)
    new_length = len(daily_stats_seen_users)
    # Update the daily stats with the difference between the lengths
    update_daily_stats("drinkers", new_length - old_length)


def update_daily_stats_purchase(user_id, drink_id, quantity, rondje, price_per_one):
    update_daily_stats_drinker(user_id)
    # If the price is zero, we do not add this purchase as it is added somewhere else
    if price_per_one > 0 and drink_id != settings['dinner_product_id']:
        update_daily_stats('purchases', 1)
    # If this purchase is a round, we add it to the number of rounds given today
    if rondje:
        update_daily_stats('rounds', 1)
    # If it is not a round, we add it to the stats per product
    else:
        update_daily_stats_product(drink_id, quantity)


def get_drinking_score():
    # The "maximum" score.
    max_score = 150

    # Calculate the begin time, which is two hours ago
    begin_time = datetime.now() - timedelta(hours=2)
    # Calculate the amount of alcohol in mL that has been drunk in the last two hours
    alcohol = db.session.query(func.sum(Purchase.amount * Product.alcohol * Product.volume))\
        .filter(and_(Purchase.timestamp > begin_time, Purchase.product_id == Product.id, Purchase.round == False))\
        .first()[0] or 0
    # The number of people that has a drink in the last two hours
    drinkers = db.session.query(Purchase.user_id)\
        .filter(and_(Purchase.timestamp > begin_time, Purchase.round == False))\
        .group_by(Purchase.user_id).count()

    # How much alcohol one person drank on average
    alcohol_per_person = alcohol / drinkers if drinkers > 0 else 0

    # All product objects that have the category "shots"
    shots = get_all_products_from_category('Shots')

    # Get the number of unique shots that have been done in the last two hours
    nr_of_unique_shots = db.session.query(Purchase.product_id)\
        .filter(and_(Purchase.timestamp > begin_time, Purchase.round == False, Purchase.product_id.in_(shots)))\
        .group_by(Purchase.product_id).count()

    # nr_of_total_shots = db.session.query(Purchase.id)\
    #     .filter(and_(Purchase.timestamp > begin_time, Purchase.round == False, Purchase.product_id.in_(shots))).count()

    # Calculate the percentage: the maximum is 100, so we take the minimum of our calculated percentage and 100.
    # Then, we multiply the amount of alcohol per person by the multipliers (in this case, only the number of unique
    # shots). Then, we divide this by the maximum score and multiply by 100.
    percentage = min(100, (alcohol_per_person * (nr_of_unique_shots * 0.02 + 1)) / max_score * 100)
    return percentage


def get_yesterday_for_today(enddate):
    if enddate.hour < 12:
        begindate = enddate - timedelta(days=1)
    else:
        begindate = enddate
    return datetime(begindate.year, begindate.month, begindate.day, 12, 0, 0)


def top_n(count, data, n):
    data.sort(key=getStatValue, reverse=True)
    if len(data) <= n:
        size = len(data)
    else:
        size = n - 1

    ids = [data[i][0] for i in range(0, size)]
    labels = [data[i][1] for i in range(0, size)]
    values = [data[i][2] for i in range(0, size)]

    if len(data) - size >= 2:
        sum = 0
        for i in range(size, len(data)):
            sum = sum + data[i][2]
        ids.append(0)
        values.append(sum)
        labels.append("Overig")

    return ids, values, labels


def topall(count, data):
    data.sort(key=getStatValue, reverse=True)
    size = len(data)
    ids = [data[i][0] for i in range(0, size)]
    labels = [data[i][1] for i in range(0, size)]
    values = [data[i][2] for i in range(0, size)]

    return ids, values, labels


def balance_over_time_user(userid, parsedbegin, parsedend):
    transactions = Transaction.query.filter(and_(Transaction.user_id == userid, Transaction.timestamp >= parsedbegin, Transaction.timestamp <= parsedend)).all()

    datat = []
    for t in transactions:
        datat.append({
            "x": str(t.timestamp.strftime("%Y-%m-%d %H:%M:%S")),
            "y": t.newbal
        })

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

    return datat, idw, labelw, valuew


def most_bought_products_per_user(userid, parsedbegin, parsedend, n=20):
    count = {}

    purchases = Purchase.query.filter(and_(Purchase.user_id == userid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend, Purchase.round == False, Purchase.product_id != settings['dinner_product_id'])).all()

    for p in purchases:
        if p.product_id not in count:
            count[p.product_id] = p.amount
        else:
            count[p.product_id] = count[p.product_id] + p.amount

    data = []
    for p_id, amount in count.items():
        data.append((p_id, Product.query.get(p_id).name, round_down(amount)))
    ids, values, labels = top_n(count, data, n)

    return ids, values, labels


def most_bought_of_one_product_by_groups(drinkid, parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(
        and_(Purchase.product_id == drinkid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend, Purchase.round == False)).all()

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

    datag = []
    for g_id, amount in count_groups.items():
        datag.append((g_id, Usergroup.query.get(g_id).name, round_down(amount)))
    idsg, valuesg, labelsg = top_n(count_groups, datag, 20)

    return idsg, valuesg, labelsg


def most_bought_of_one_product_by_users(drinkid, parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(
        and_(Purchase.product_id == drinkid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend, Purchase.round == False)).all()

    for pur in purchases:
        if pur.user_id not in count:
            count[pur.user_id] = pur.amount
        else:
            count[pur.user_id] = count[pur.user_id] + pur.amount

    datau = []
    for u_id, amount in count.items():
        datau.append((u_id, User.query.get(u_id).name, round_down(amount)))
    idsu, valuesu, labelsu = top_n(count, datau, 20)

    return idsu, valuesu, labelsu


def most_bought_of_one_product_by_users_today(drinkid, parsedend):
    parsedbegin = get_yesterday_for_today(parsedend)
    return most_bought_of_one_product_by_users(drinkid, parsedbegin, parsedend)


def most_bought_of_one_product_by_groups_from_group(drinkid, groupid, parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(and_(Purchase.product_id == drinkid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend, Purchase.round == False)).all()

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

    datag = []
    for g_id, amount in count_groups.items():
        datag.append((g_id, Usergroup.query.get(g_id).name, round_down(amount)))

    idsg, valuesg, labelsg = top_n(count_groups, datag, 20)

    return idsg, valuesg, labelsg


def most_bought_of_one_product_by_users_from_group(drinkid, groupid, parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(and_(Purchase.product_id == drinkid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend, Purchase.round == False)).all()

    for pur in purchases:
        if User.query.get(pur.user_id).usergroup_id == groupid:
            if pur.user_id not in count:
                count[pur.user_id] = pur.amount
            else:
                count[pur.user_id] = count[pur.user_id] + pur.amount

    datau = []
    for u_id, amount in count.items():
        datau.append((u_id, User.query.get(u_id).name, round_down(amount)))
    idsu, valuesu, labelsu = top_n(count, datau, 20)

    return idsu, valuesu, labelsu


def most_bought_products_by_users(parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(and_(Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend,
                                           Purchase.product_id != settings['dinner_product_id'],
                                           Purchase.round == False)).all()
    for pur in purchases:
        if pur.product_id not in count:
            count[pur.product_id] = pur.amount
        else:
            count[pur.product_id] = count[pur.product_id] + pur.amount

    datap = []
    for p_id, amount in count.items():
        datap.append((p_id, Product.query.get(p_id).name, round_down(amount)))

    return topall(count, datap)


def most_bought_products_by_users_today(parsedend):
    parsedbegin = get_yesterday_for_today(parsedend)
    return most_bought_products_by_users(parsedbegin, parsedend)


def most_alcohol_drank_by_users(parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(and_(Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend,
                                           Purchase.round == False, Purchase.product_id != settings['dinner_product_id'], Purchase.price > 0)).all()

    for pur in purchases:
        alcohol = Product.query.get(pur.product_id).alcohol
        if pur.user_id not in count:
            count[pur.user_id] = pur.amount * alcohol
        else:
            count[pur.user_id] = count[pur.user_id] + pur.amount * alcohol

    datau = []
    for u_id, amount in count.items():
        datau.append((u_id, User.query.get(u_id).name, float(amount)))
    idsu, valuesu, labelsu = top_n(count, datau, 20)

    return idsu, valuesu, labelsu


def most_alcohol_drank_by_users_today(parsedend):
    parsedbegin = get_yesterday_for_today(parsedend)
    return most_alcohol_drank_by_users(parsedbegin, parsedend)


init_daily_stats()
init_max_stats()
