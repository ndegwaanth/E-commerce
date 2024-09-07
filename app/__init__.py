import os
from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Use environment variables for config
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

# Setup Flask-PyMongo connection
mongo = PyMongo(app)

# Import the routes after app creation
from .routes import main_bp
app.register_blueprint(main_bp)

