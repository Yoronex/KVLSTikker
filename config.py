import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    VIEW_ONLY = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'scouting-kornet-van-limburg-stirum-olst-wijhe'
    SQLALCHEMY_DATABASE_LOC = os.path.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + SQLALCHEMY_DATABASE_LOC
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/products')
    LOG_FOLDER = os.path.join(basedir, 'logs')
    BACKUP_FOLDER = os.path.join(basedir, 'backup')
    ALBUM_COVER_FOLDER = os.path.join(basedir, 'app/static/covers')
    SPOTIFY_CACHE_FOLDER = os.path.join(basedir, 'spotifycache')
    DOCUMENT_FOLDER = os.path.join(basedir, 'documents')
    SOUNDBOARD_FOLDER = os.path.join(basedir, 'app/static/soundboard')
    VIDEOS_FOLDER = os.path.join(basedir, 'app/static/videos')
    MAX_BACKUPS = 20
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'gif'}
    ADMIN_PASSWORD = "knotgang"
    STATS_BEGINDATE = "2019-01-01"
    MAIL_SERVER = 'mail.kvls.nl'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ("KVLS Tikker", "tikker@kvls.nl")
    DEBT_MAXIMUM = 0.0  # Negative balance is
    SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5000/api/spotify/login'
    SPOTIPY_SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'
    SPOTIPY_CACHE = '.spotipyoauthcache'
    CALENDAR_URL = 'https://drive.kvls.nl/remote.php/dav/public-calendars/BKWDW9PJT2mmoRa4?export'
    CALENDAR_UPDATE_INTERVAL = 30 * 60
    PROFIT_PERCENTAGE = 0.8  # Percentage of profit that goes to the GROUP. The rest goes to the bar!
