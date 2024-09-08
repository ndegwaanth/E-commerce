from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from .forms import RegistrationForm
from . import mongo

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', form=form)

@main_bp.route('/home')
def home():
    return 'Home Page'

@main_bp.route('/add_user', methods=['POST'])
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        mongo.db.user.insert_one({'Username': username, 'Email': email, 'Password': password, 'Comfirm Password': confirm_password})

        return redirect(url_for('main.home'))

    return render_template('register.html')