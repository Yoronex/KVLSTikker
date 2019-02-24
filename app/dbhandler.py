from app import app, db, dbhandler
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction
from flask import flash
from werkzeug.utils import secure_filename
import os

class dbhandler():
    def getdb(self):
        global db_obj
        if db_obj is None:
            db_obj = dbhandler()
        return db_obj

    def addpurchase(self, drink_id, user_id, quantity):
        drink = Product.query.get(drink_id)
        user = User.query.get(user_id)
        user.balance = user.balance - float(drink.price) * quantity
        purchase = Purchase(user_id=user.id, product_id=drink.id, price=drink.price, amount=quantity)
        db.session.add(purchase)
        db.session.commit()
        balchange = -drink.price * quantity
        transaction = Transaction(user_id=user.id, purchase_id=purchase.id, balchange=balchange, newbal=user.balance)
        db.session.add(transaction)
        db.session.commit()
        flash("{}x {} voor {} verwerkt".format(quantity, drink.name, user.name), "success")

    def addbalance(self, user_id, amount):
        upgrade = Upgrade(user_id=user_id, amount=amount)
        db.session.add(upgrade)
        db.session.commit()
        user = User.query.get(upgrade.user_id)
        user.balance = user.balance + float(amount)
        transaction = Transaction(user_id=user_id, upgrade_id=upgrade.id, balchange=upgrade.amount,
                                  newbal=user.balance)
        db.session.add(transaction)
        db.session.commit()
        flash("Gebruiker {} heeft succesvol opgewaardeerd met €{}".format(user.name, str("%.2f" % upgrade.amount).replace(".", ",")), "success")

    def adddrink(self, name, price, image):
        product = Product(name=name, price=price, purchaseable=True)
        db.session.add(product)
        db.session.commit()
        filename, file_extension = os.path.splitext(secure_filename(image.filename))
        filename = str(product.id) + file_extension
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        flash("Product {} succesvol aangemaakt".format(product.name), "success")

    def adduser(self, name, group):
        user = User(name=name, usergroup_id=group)
        db.session.add(user)
        db.session.commit()
        flash("Gebruiker {} succesvol geregistreerd".format(user.name), "success")

    def addusergroup(self, name):
        usergroup = Usergroup(name=name)
        db.session.add(usergroup)
        db.session.commit()
        flash("Groep {} succesvol aangemaakt".format(usergroup.name), "success")

    def deluser(self, user_id):
        user = User.query.get(user_id)
        for t in user.transactions.all():
            db.session.delete(t)
        for u in user.upgrades.all():
            db.session.delete(u)
        for p in user.purchases.all():
            db.session.delete(p)
        db.session.delete(user)
        db.session.commit()
        flash("Gebruiker {} verwijderd".format(user.name), "success")

    def delpurchase(self, transaction_id):
        transaction = Transaction.query.get(transaction_id)
        if transaction.purchase_id is None:
            upgrade = Upgrade.query.get(transaction.upgrade_id)
            db.session.delete(upgrade)
        else:
            purchase = Purchase.query.get(transaction.purchase_id)
            db.session.delete(purchase)
        for t in Transaction.query.filter(Transaction.user_id == transaction.user_id, Transaction.timestamp > transaction.timestamp).all():
            t.newbal = t.newbal - transaction.balchange
        user = User.query.get(transaction.user_id)
        user.balance = user.balance - transaction.balchange
        db.session.delete(transaction)
        db.session.commit()
        flash("Transactie met ID {} succesvol verwijderd!".format(transaction.id), "success")

    def deldrink(self, drink_id):
        product = Product.query.get(drink_id)
        product.purchaseable = False
        db.session.commit()
        flash('Product {} is niet meer beschikbaar'.format(product.name), "success")

    def delusergroup(self, usergroup_id):
        usergroup = Usergroup.query.get(usergroup_id)
        db.session.delete(usergroup)
        db.session.commit()
        flash("Groep {} verwijderd".format(usergroup.name), "success")

    def editdrink_attr(self, product_id, name, price, purchaseable):
        product = Product.query.get(product_id)
        product.name = name
        product.price = price
        product.purchaseable = purchaseable
        db.session.commit()
        flash("Product {} (ID: {}) succesvol aangepast!".format(product.name, product.id), "success")

    def editdrink_image(self, product_id, image):
        product = Product.query.get(product_id)
        filename, file_extension = os.path.splitext(secure_filename(image.filename))
        filename = str(product.id) + file_extension
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        flash("Afbeelding van product {} (ID: {}) succesvol aangepast!".format(product.name, product.id), "success")
