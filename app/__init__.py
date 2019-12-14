import locale
import logging
from flask import Flask
from config import Config
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_breadcrumbs import Breadcrumbs
from logging.handlers import RotatingFileHandler
import os
import zipfile
from datetime import datetime

# locale.setlocale(locale.LC_ALL, 'nl_NL')
locale.setlocale(locale.LC_ALL, 'nld_nld')
app = Flask(__name__)
app.config.from_object(Config)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}, r"/socket.io/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")  # Needs to be changed later for Tikker BigScreen

if not os.path.exists(app.config['ALBUM_COVER_FOLDER']):
    os.makedirs(app.config['ALBUM_COVER_FOLDER'])

if not os.path.exists(app.config['BACKUP_FOLDER']):
    os.makedirs(app.config['BACKUP_FOLDER'])

if not os.path.exists(app.config['SPOTIFY_CACHE_FOLDER']):
    os.makedirs(app.config['SPOTIFY_CACHE_FOLDER'])

list_of_files = os.listdir(app.config['BACKUP_FOLDER'])
if len(list_of_files) >= app.config['MAX_BACKUPS']:
    full_paths = [os.path.join(app.config['BACKUP_FOLDER'], str(x)) for x in list_of_files]
    oldest_file = min(full_paths, key=os.path.getctime)
    os.remove(oldest_file)
zip_path = os.path.join(app.config['BACKUP_FOLDER'], datetime.now().strftime("%Y%m%d%H%M%S") + ".zip")
zipfile.ZipFile(zip_path, mode='w').write(app.config['SQLALCHEMY_DATABASE_LOC'])

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


def get_date_today():
    str = datetime.now().strftime("%Y-%m-%d")
    return str


def is_18min(u):
        today = datetime.today()
        days_in_year = 365.2425
        age = int((today - u.birthday).days / days_in_year)
        if age < 18:
            return True
        else:
            return False


app.jinja_env.globals.update(get_date_today=get_date_today)
app.jinja_env.globals.update(is_18min=is_18min)
