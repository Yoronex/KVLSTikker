from sqlalchemy import and_, or_, func
from app import app
from app.dbhandler import dbhandler
from app.forms import LoginForm, UserRegistrationForm, UpgradeBalanceForm, UserGroupRegistrationForm, DrinkForm, \
    ChangeDrinkForm, ChangeDrinkImageForm, AddInventoryForm, PayOutProfitForm
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction, Inventory
from datetime import datetime, timedelta


def getStatValue(elem):
    return elem[2]


def getIDnumber(elem):
    return elem[0]


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
