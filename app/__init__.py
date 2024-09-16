import os
from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from gridfs import GridFS
from flask_login import LoginManager
from bson import ObjectId
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

load_dotenv()

app = Flask(__name__)

bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["MONGO_URI_3"] = os.getenv("MONGO_URI_3")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")


mongo = PyMongo(app)

fs = GridFS(mongo.db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    user_dict = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_dict:
        from app.models import User
        return User(user_dict)
    return None

from .routes import main_bp
from .data import data_bp
from app.admin import admin_bp

app.register_blueprint(main_bp)
app.register_blueprint(data_bp, url_prefix='/data')
app.register_blueprint(admin_bp, url_prefix='/admin')
