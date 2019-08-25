import logging
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_breadcrumbs import Breadcrumbs
from logging.handlers import RotatingFileHandler
import os

# TODO: zipping app.db every boot
# TODO: shutdown url

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
Bootstrap(app)
breadcrumbs = Breadcrumbs(app=app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True

from app import routes, models

if not app.debug:
    if not os.path.exists(app.config["LOG_FOLDER"]):
        os.makedirs(app.config["LOG_FOLDER"])
    file_handler = RotatingFileHandler(app.config['LOG_FOLDER'] + 'tikker.log', maxBytes=102400, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Tikker startup')
