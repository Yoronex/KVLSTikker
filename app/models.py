from datetime import datetime
from app import db
import pickle
from sqlalchemy import PickleType, and_


def dump_datetime(value):
    """Deserialize datetime object into string form for JSON processing."""
    if value is None:
        return None
    return [value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S")]


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    usergroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))
    balance = db.Column(db.Float, default=0)
    upgrades = db.relationship('Upgrade', backref='user', lazy='dynamic')
    purchases = db.relationship('Purchase', backref='user', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    profitgroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))
    birthday = db.Column(db.DateTime)


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


class Recipe(db.Model):
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    quantity = db.Column(db.Integer)

    def __repr__(self):
        return '<Ingredient {} voor {}>'.format(self.ingredient_id, self.product_id)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    image = db.Column(db.String)
    hoverimage = db.Column(db.String)
    #components = db.Column(db.PickleType, nullable=True)
    recipe = db.relationship('Recipe', backref='product', lazy='dynamic', foreign_keys=[Recipe.product_id])
    recipe_input = db.Column(db.PickleType, nullable=True)
    purchaseable = db.Column(db.Boolean)
    purchases = db.relationship('Purchase', backref='product', lazy='dynamic')
    price = db.Column(db.Float)
    volume = db.Column(db.Float, nullable=True)  # amount of ml
    unit = db.Column(db.String, nullable=True)  # e.g. bottle or 50ml
    alcohol = db.Column(db.Float, nullable=True)  # percentage as float between 0 and 1
    inventory_warning = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return '<Product {} voor {}>'.format(self.name, self.price)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'recipe_input': self.recipe_input,
            'purchaseable': self.purchaseable,
            'price': self.price
        }


class Inventory_usage(db.Model):
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), primary_key=True)
    quantity = db.Column(db.Float)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now())
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    transactions = db.relationship('Transaction', backref='purchase', lazy='dynamic')
    amount = db.Column(db.Float)
    price = db.Column(db.Float)
    round = db.Column(db.Boolean, default=False)
    #inventory_usage = db.relationship('Inventory Usage', backref='purchase', lazy='dynamic')

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

    @property
    def serialize(self):
        return {
            'id': self.id,
            'timestamp': dump_datetime(self.timestamp),
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price_before_profit': self.price_before_profit,
            'note': self.note
        }

