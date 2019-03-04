from datetime import datetime
from app import db


class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    users = db.relationship('User', backref='group', lazy='dynamic')

    def __repr__(self):
        return '{}'.format(self.name)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    usergroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))
    balance = db.Column(db.Float, default=0)
    upgrades = db.relationship('Upgrade', backref='user', lazy='dynamic')
    purchases = db.relationship('Purchase', backref='user', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.name)


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
    purchaseable = db.Column(db.Boolean)
    purchases = db.relationship('Purchase', backref='product', lazy='dynamic')
    price = db.Column(db.Float)

    def __repr__(self):
        return '<Product {} voor {}>'.format(self.name, self.price)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    transactions = db.relationship('Transaction', backref='purchase', lazy='dynamic')
    amount = db.Column(db.Integer)
    price = db.Column(db.Float)

    def __repr__(self):
        return '<Purchase {}>'.format(self.price)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'))
    upgrade_id = db.Column(db.Integer, db.ForeignKey('upgrade.id'))
    balchange = db.Column(db.Float)
    newbal = db.Column(db.Float)