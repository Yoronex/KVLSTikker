import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'scouting-kornet-van-limburg-stirum-olst-wijhe'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = basedir + '/app/static/products/'
    LOG_FOLDER = basedir + '/logs/'
    ALLOWED_EXTENSIONS = set(['jpg', 'png', 'bmp', 'gif'])
    ADMIN_PASSWORD = "knotgang"
