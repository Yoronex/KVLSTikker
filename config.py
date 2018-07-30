import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'scouting-kornet-van-limburg-stirum-olst-wijhe'