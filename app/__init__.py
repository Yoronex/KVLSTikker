from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_breadcrumbs import Breadcrumbs

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
Bootstrap(app)
breadcrumbs = Breadcrumbs(app=app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True


from app import routes, models