from datetime import datetime
from app import db
import pickle
from sqlalchemy import PickleType, and_


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    usergroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))
    balance = db.Column(db.Float, default=0)
    upgrades = db.relationship('Upgrade', backref='user', lazy='dynamic')
    purchases = db.relationship('Purchase', backref='user', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    profitgroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))

    #usergroup = db.relationship('Usergroup', foreign_keys=[usergroup_id])
    #profitgroup = db.relationship('Usergroup', foreign_keys=[profitgroup_id])


    def __repr__(self):
        return '<User {}>'.format(self.name)


class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    profit = db.Column(db.Float, default=0.0)
    users = db.relationship('User', backref='group', lazy='dynamic', foreign_keys=[User.usergroup_id])

    def __repr__(self):
        return '{}'.format(self.name)


class Upgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    transactions = db.relationship('Transaction', backref='upgrade', lazy='dynamic')
    amount = db.Column(db.Float)

    def __repr__(self):
        return '<Upgrade {}>'.format(self.amount)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    image = db.Column(db.String)
    hoverimage = db.Column(db.String)
    components = db.Column(db.PickleType, nullable=True)
    purchaseable = db.Column(db.Boolean)
    purchases = db.relationship('Purchase', backref='product', lazy='dynamic')
    price = db.Column(db.Float)
    inventory_warning = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return '<Product {} voor {}>'.format(self.name, self.price)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    transactions = db.relationship('Transaction', backref='purchase', lazy='dynamic')
    amount = db.Column(db.Float)
    price = db.Column(db.Float)

    def __repr__(self):
        return '<Purchase {} by {}>'.format(self.product_id, self.user_id)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'))
    upgrade_id = db.Column(db.Integer, db.ForeignKey('upgrade.id'))
    balchange = db.Column(db.Float)
    newbal = db.Column(db.Float)


# -- inventory management
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Float)
    price_before_profit = db.Column(db.Float)
    note = db.Column(db.String, nullable=True)
