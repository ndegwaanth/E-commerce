import os
from flask import Flask, current_app
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from gridfs import GridFS

load_dotenv()

app = Flask(__name__)

app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["MONGO_URI_3"] = os.getenv("MONGO_URI_3")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")


mongo = PyMongo(app)

fs = GridFS(mongo.db)

from .routes import main_bp
app.register_blueprint(main_bp)
