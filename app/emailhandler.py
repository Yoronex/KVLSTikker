import socket
from datetime import datetime, timedelta
from smtplib import SMTPRecipientsRefused

from flask import render_template, flash
from flask_mail import Message
from sqlalchemy import and_

from app import app, mail, dbhandler, db, statshandler
from app.models import User, Purchase, Transaction, Product, Upgrade, Usergroup

enabled = True
if app.config['MAIL_PASSWORD'] is '':
    enabled = False
    disable_reason = "Er is geen wachtwoord van de mailserver bekend"


def set_default_lastoverview():
    for u in User.query.all():
        if u.lastoverview is None:
            u.lastoverview = datetime.strptime("2019-07-01", "%Y-%m-%d")
            db.session.commit()


def send_debt_emails():
    users = User.query.all()
    emails = create_debt_emails(users) + create_treasurer_email(False)
    try:
        send_emails(emails)
        flash("Emails succesvol verstuurd!", "success")
        dbhandler.update_settings('last_debt_email', datetime.now().strftime("%Y-%m-%d"))
    except socket.gaierror:
        flash("Kon geen verbinding maken met de KVLS Server. Weet je zeker dat de computer internet heeft?", "danger")


def send_overview_emails():
    users = User.query.all()
    begindate = datetime.strptime(dbhandler.settings['last_overview_email'], "%Y-%m-%d")
    enddate = datetime.now().replace(day=1)
    if enddate.weekday() >= 4:
        enddate += timedelta(days=7 - enddate.weekday())

    emails = create_overview_dinner_emails(users, begindate, enddate) + create_overview_emails(users, begindate, enddate) + create_debt_emails(users) + create_treasurer_email(True)

    try:
        send_emails(emails)
        flash("Emails succesvol verstuurd!", "success")
        dbhandler.update_settings('last_overview_email', enddate.strftime("%Y-%m-%d"))
        dbhandler.update_settings('last_debt_email', enddate.strftime("%Y-%m-%d"))
    except socket.gaierror:
        flash("Kon geen verbinding maken met de KVLS Server. Weet je zeker dat de computer internet heeft?", "danger")


def monthlist_fast(dates):
    #  start, end = [datetime.strptime(_, "%Y-%m-%d") for _ in dates]
    start, end = dates[0], dates[1]
    total_months = lambda dt: dt.month + 12 * dt.year
    mlist = []
    for tot_m in range(total_months(start) - 1, total_months(end)):
        y, m = divmod(tot_m, 12)
        mlist.append(datetime(y, m + 1, 1).strftime("%B"))
    del mlist[-1]

    months = ""
    for i in range(0, len(mlist)):
        if i == len(mlist) - 1:
            months += mlist[i]
        elif i == len(mlist) - 2:
            months += mlist[i] + " en "
        else:
            months += mlist[i] + ", "

    return months


def create_debt_emails(users):
    emails = []

    for u in users:
        if u.balance < app.config['DEBT_MAXIMUM']:
            result = {'html': render_template('email/debt.html', user=u),
                      'body': render_template('email/debt.txt', user=u),
                      'recipients': [u.email], 'subject': "Je hebt een te hoge schuld!"}
            emails.append(result)

    return emails


def create_overview_dinner_emails(users, begindate, enddate):
    emails = []

    for u in users:
        purchases = Purchase.query.filter(
            and_(Purchase.product_id == dbhandler.settings['dinner_product_id'], Purchase.user_id == u.id,
                 Purchase.timestamp > begindate, Purchase.timestamp < enddate)).all()
        if len(purchases) > 0:
            months = monthlist_fast([begindate, enddate])
            total = 0
            for p in purchases:
                total += p.amount * p.price

            result = {'html': render_template('email/overview_dinner.html', user=u, purchases=purchases, total=total,
                                              months=months),
                      'body': render_template('email/overview_dinner.txt', user=u, purchases=purchases, total=total,
                                              months=months),
                      'recipients': [u.email], 'subject': "Maandelijks overzicht Stam Opkomstdiner {}".format(months)}
            emails.append(result)

    return emails


def create_overview_emails(users, begindate, enddate):
    emails = []
    nr_of_products = Product.query.count()

    for u in users:
        transactions = Transaction.query.filter(and_(Transaction.user_id == u.id, Transaction.timestamp > begindate, Transaction.timestamp < enddate)).all()
        if len(transactions) > 0:
            months = monthlist_fast([begindate, enddate])

            product_ids, product_amount, product_names = statshandler.most_bought_products_per_user(u.id, begindate, enddate,
                                                                                             nr_of_products)

            result = {'html': render_template('email/overview.html', user=u, transactions=transactions, Product=Product,
                                              Purchase=Purchase, Upgrade=Upgrade, months=months,
                                              product_name=product_names, product_amount=product_amount),
                      'body': render_template('email/overview.txt', user=u, transactions=transactions, Product=Product,
                                              Purchase=Purchase, Upgrade=Upgrade, months=months,
                                              product_name=product_names, product_amount=product_amount),
                      'recipients': [u.email], 'subject': "Maandelijks overzicht transacties {}".format(months)}
            emails.append(result)

    return emails


def create_treasurer_email(also_overview):
    if dbhandler.settings['treasurer-email'] != "":
        usergroups = Usergroup.query.all()
        products = []
        for p in Product.query.filter(and_(Product.recipe_input == None), (Product.purchaseable == True)).all():
            result = dbhandler.get_inventory_stock(p.id)
            result[0]['name'] = p.name
            result[0]['id'] = p.id
            result[0]['inventory_value'] = dbhandler.calc_inventory_value(p.id)
            products.append(result[0])

        return [{'html': render_template('email/treasurer.html', User=User, usergroups=usergroups, products=products,
                                         also_overview=also_overview, maxdebt=app.config["DEBT_MAXIMUM"]),
                 'body': render_template('email/treasurer.txt', User=User, usergroups=usergroups, products=products,
                                         also_overview=also_overview, maxdebt=app.config["DEBT_MAXIMUM"]),
                 'recipients': [dbhandler.settings['treasurer-email']],
                 'subject': "Actuele schulden, winstpotjes en inventaris"}]
    else:
        return []


def send_emails(emails):
    with mail.connect() as conn:
        for e in emails:
            try:
                msg = Message(recipients=e['recipients'], html=e['html'], body=e['body'], subject=e['subject'])
                conn.send(msg)
            except SMTPRecipientsRefused:
                error = 'Kon niet de mail "{}" versturen naar {}'.format(e['subject'], e['recipients'])
                app.logger.info(error)
                flash(error)
