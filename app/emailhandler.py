import socket
from datetime import datetime, timedelta

from flask import render_template, flash
from flask_mail import Message
from sqlalchemy import and_

from app import app, mail, dbhandler, db
from app.models import User, Purchase, Transaction, Product, Upgrade

enabled = True
if app.config['MAIL_PASSWORD'] is '':
    enabled = False
    disable_reason = "Er is geen wachtwoord van de mailserver bekend"


def set_default_lastoverview():
    for u in User.query.all():
        if u.lastoverview is None:
            u.lastoverview = datetime.strptime("2019-07-01", "%Y-%m-%d")
            db.session.commit()


def test_debt_email():
    emails = create_debt_emails([User.query.get(1)])
    send_emails(emails)


def test_dinner_overview_email():
    emails = create_overview_dinner_emails([User.query.get(1)])
    send_emails(emails)


def test_overview_email():
    emails = create_overview_emails([User.query.get(1)])
    send_emails(emails)


def send_debt_emails():
    users = User.query.all()
    emails = create_debt_emails(users)
    try:
        send_emails(emails)
        flash("Emails succesvol verstuurd!", "success")
        dbhandler.update_settings('last_debt_email', datetime.now().strftime("%Y-%m-%d"))
    except socket.gaierror:
        flash("Kon geen verbinding maken met de KVLS Server. Weet je zeker dat de computer internet heeft?", "danger")


def send_overview_emails():
    users = User.query.all()
    begindate = datetime.strptime(dbhandler.settings['last_overview_email'], "%Y-%m-%d")
    #  enddate = datetime.now().replace(day=1)
    enddate = datetime(year=2020, month=1, day=1)
    if enddate.weekday() >= 4:
        enddate += timedelta(days=7 - enddate.weekday())

    emails = create_overview_dinner_emails(users, begindate, enddate) + create_overview_emails(users, begindate, enddate) + create_debt_emails(users)

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

    for u in users:
        transactions = Transaction.query.filter(and_(Transaction.user_id == u.id, Transaction.timestamp > begindate, Transaction.timestamp < enddate)).all()
        if len(transactions) > 0:
            months = monthlist_fast([begindate, enddate])

            result = {'html': render_template('email/overview.html', user=u, transactions=transactions, Product=Product,
                                              Purchase=Purchase, Upgrade=Upgrade, months=months),
                      'body': render_template('email/overview.txt', user=u, transactions=transactions, Product=Product,
                                              Purchase=Purchase, Upgrade=Upgrade, months=months),
                      'recipients': [u.email], 'subject': "Maandelijks overzicht transacties {}".format(months)}
            emails.append(result)

    return emails


def send_emails(emails):
    with mail.connect() as conn:
        for e in emails:
            msg = Message(recipients=e['recipients'], html=e['html'], body=e['body'], subject=e['subject'])
            conn.send(msg)
