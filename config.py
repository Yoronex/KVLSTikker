import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'scouting-kornet-van-limburg-stirum-olst-wijhe'
    SQLALCHEMY_DATABASE_LOC = os.path.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + SQLALCHEMY_DATABASE_LOC
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/products')
    LOG_FOLDER = os.path.join(basedir, 'logs')
    BACKUP_FOLDER = os.path.join(basedir, 'backup')
    ALBUM_COVER_FOLDER = os.path.join(basedir, 'app/static/covers')
    SPOTIFY_CACHE_FOLDER = os.path.join(basedir, 'spotifycache')
    MAX_BACKUPS = 20
    ALLOWED_EXTENSIONS = {'jpg', 'png', 'bmp', 'gif'}
    ADMIN_PASSWORD = "knotgang"
    STATS_BEGINDATE = "2019-01-01"
