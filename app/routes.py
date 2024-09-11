from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from .forms import RegistrationForm, LoginForm


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('main.home'))
    return render_template('register.html', form=form)

@main_bp.route('/home')
def home():
    return 'Home Page'

@main_bp.route('/add_user', methods=['POST'])
def add_user():
    if request.method == 'POST':
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        from . import mongo

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        confirm_password = request.form.get('confirm_password')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf8')
        hashed_confirm_password = bcrypt.generate_password_hash(confirm_password).decode('utf8')

        mongo.db.users.insert_one({
            'Username': username, 
            'Email': email, 
            'Password': hashed_password,
            'Confirm Password': hashed_confirm_password
        })
        return redirect(url_for('main.home'))

    return render_template('register.html')


@main_bp.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()

    # Check if the request method is POST and the form has been validated
    if form.validate_on_submit() and request.method == 'POST':
        from flask_bcrypt import Bcrypt
        from . import mongo

        bcrypt = Bcrypt()

        # Retrieve form data
        # email = form.email.data
        email = request.form.get('email')
        # password = form.password.data
        password = request.form.get('password')

        # Fetch user details from the database (assuming you're using MongoDB)
        user = mongo.db.users.find_one({'Email': email})

        # Check if user exists and if password matches
        if user and bcrypt.check_password_hash(user['Password'], password):
            # Login successful - redirect to the home page
            login_user(user)
            return redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
            return redirect(url_for('main.login'))  # Return to login page on failure

    # Render the login template for GET request or if validation fails
    return render_template('login.html', form=form)