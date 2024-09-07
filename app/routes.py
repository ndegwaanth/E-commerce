from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt


main_bp = Blueprint('homepage', __name__)
# main_bp.config['SECRETE KEY'] = 'mysecrete key'


@main_bp.route('/')
def index():
    return render_template('index.html')