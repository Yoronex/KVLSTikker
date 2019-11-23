from sqlalchemy import and_, or_, func
from app import app, db
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm, \
    ChangeDrinkForm, ChangeDrinkImageForm, AddInventoryForm, PayOutProfitForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction, Inventory, Setting
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

daily_stats_seen_users = []

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

    daily_stats["products"] = Product.query.filter(Product.purchaseable == True).count()
    daily_stats["users"] = User.query.count()
    drinkers = Purchase.query.filter(Purchase.timestamp > begindate).group_by(Purchase.user_id).all()
    for d in drinkers:
        daily_stats_seen_users.append(d.user_id)
    daily_stats["drinkers"] = len(drinkers)
    daily_stats["rounds"] = Purchase.query.filter(Purchase.timestamp > begindate, Purchase.round == True).count()
    daily_stats["purchases"] = Purchase.query.filter(Purchase.timestamp > begindate).count()

    purchases = Purchase.query.filter(Purchase.timestamp > begindate).all()
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
                max_stats[s.key] = int(s.value)


def reset_daily_stats():
    global daily_stats
    global daily_stats_seen_users

    daily_stats["drinkers"] = 0
    daily_stats["beers"] = 0
    daily_stats["mixes"] = 0
    daily_stats["shots"] = 0
    daily_stats["purchases"] = 0
    daily_stats["rounds"] = 0


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
    if user_id not in daily_stats_seen_users:
        daily_stats_seen_users.append(user_id)
        update_daily_stats("drinkers", 1)


def get_yesterday_for_today(enddate):
    if enddate.hour < 12:
        begindate = enddate - timedelta(days=1)
    else:
        begindate = enddate
    return datetime(begindate.year, begindate.month, begindate.day, 12, 0, 0)


def top10(count, data):
    data.sort(key=getStatValue, reverse=True)
    if len(count) <= 10:
        size = len(count)
    else:
        size = 9

    ids = [data[i][0] for i in range(0, size)]
    labels = [data[i][1] for i in range(0, size)]
    values = [data[i][2] for i in range(0, size)]

    if len(count) - size >= 2:
        sum = 0
        for i in range(size, len(count)):
            sum = sum + data[i][2]
        ids.append(0)
        values.append(sum)
        labels.append("Overig")

    return ids, values, labels


def topall(count, data):
    data.sort(key=getStatValue, reverse=True)
    size = len(count)
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


def most_bought_products_per_user(userid, parsedbegin, parsedend):
    count = {}

    purchases = Purchase.query.filter(and_(Purchase.user_id == userid, Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend, Purchase.round == False)).all()

    for p in purchases:
        if p.product_id not in count:
            count[p.product_id] = p.amount
        else:
            count[p.product_id] = count[p.product_id] + p.amount

    data = []
    for p_id, amount in count.items():
        data.append((p_id, Product.query.get(p_id).name, int(amount)))
    ids, values, labels = top10(count, data)

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
        datag.append((g_id, Usergroup.query.get(g_id).name, int(amount)))
    idsg, valuesg, labelsg = top10(count_groups, datag)

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
        datau.append((u_id, User.query.get(u_id).name, int(amount)))
    idsu, valuesu, labelsu = top10(count, datau)

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
        datag.append((g_id, Usergroup.query.get(g_id).name, int(amount)))

    idsg, valuesg, labelsg = top10(count_groups, datag)

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
        datau.append((u_id, User.query.get(u_id).name, int(amount)))
    idsu, valuesu, labelsu = top10(count, datau)

    return idsu, valuesu, labelsu


def most_bought_products_by_users(parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(and_(Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend)).all()
    for pur in purchases:
        if pur.product_id not in count:
            count[pur.product_id] = pur.amount
        else:
            count[pur.product_id] = count[pur.product_id] + pur.amount

    datap = []
    for p_id, amount in count.items():
        datap.append((p_id, Product.query.get(p_id).name, int(amount)))

    return topall(count, datap)


def most_bought_products_by_users_today(parsedend):
    parsedbegin = get_yesterday_for_today(parsedend)
    return most_bought_products_by_users(parsedbegin, parsedend)


def most_alcohol_drank_by_users(parsedbegin, parsedend):
    count = {}
    purchases = Purchase.query.filter(and_(Purchase.timestamp >= parsedbegin, Purchase.timestamp <= parsedend,
                                           Purchase.round == False)).all()

    for pur in purchases:
        alcohol = Product.query.get(pur.product_id).alcohol
        if pur.user_id not in count:
            count[pur.user_id] = pur.amount * alcohol
        else:
            count[pur.user_id] = count[pur.user_id] + pur.amount * alcohol

    datau = []
    for u_id, amount in count.items():
        datau.append((u_id, User.query.get(u_id).name, float(amount)))
    idsu, valuesu, labelsu = top10(count, datau)

    return idsu, valuesu, labelsu


def most_alcohol_drank_by_users_today(parsedend):
    parsedbegin = get_yesterday_for_today(parsedend)
    return most_alcohol_drank_by_users(parsedbegin, parsedend)


init_daily_stats()
init_max_stats()
