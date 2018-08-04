from app import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    group_id = db.Column(db.Integer)
    balance = db.Column(db.Float)
    password_hash = db.Column(db.String(128))
    upgrades = db.relationship('Upgrade', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.name)

class Upgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)

    def __repr__(self):
        return '<Upgrade {}>'.format(self.amount)