from app import db
from datetime import datetime


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
    upgrades = db.relationship('Upgrade', backref='author', lazy='dynamic')
    purchases = db.relationship('Purchase', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.name)


class Upgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)

    def __repr__(self):
        return '<Upgrade {}>'.format(self.amount)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    purchaseable = db.Column(db.Boolean)
    purchases = db.relationship('Purchase', backref='product', lazy='dynamic')

    def __repr__(self):
        return '<Product {}>'.format(self.name)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    price = db.Column(db.Float)

    def __repr__(self):
        return '<Purchase {}>'.format(self.price)
