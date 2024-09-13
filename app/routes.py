from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from .forms import RegistrationForm, LoginForm
from gridfs import GridFS
import os

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

    if form.validate_on_submit() and request.method == 'POST':
        from flask_bcrypt import Bcrypt
        from . import mongo

        bcrypt = Bcrypt()

        # Retrieve form data
        # email = form.email.data
        email = request.form.get('email')
        # password = form.password.data
        password = request.form.get('password')

        user = mongo.db.users.find_one({'Email': email})

        if user and bcrypt.check_password_hash(user['Password'], password):
            login_user(user)
            return redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
            return redirect(url_for('main.login'))  # Return to login page on failure

    return render_template('login.html', form=form)

@main_bp.route('/upload-images')
def upload_images():
    from . import mongo
    # Get the path to the static/images directory
    images_path = os.path.join(current_app.root_path, 'static/images')
    
    # Initialize GridFS
    fs = GridFS(mongo.db)

    # Iterate over all directories and files in the images_path
    for root, dirs, files in os.walk(images_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.relpath(file_path, images_path)
            folder_name = os.path.basename(root)  # Get the folder name

            # Check if file already exists in GridFS
            existing_file = fs.find_one({'filename': file_name})
            if existing_file:
                print(f"File '{file_name}' already exists in MongoDB.")
                continue  # Skip uploading this file

            # Open and upload the file to GridFS with folder metadata
            with open(file_path, 'rb') as f:
                fs.put(f, filename=file_name, metadata={'folder': folder_name})

    flash('All images have been uploaded successfully.')
    return redirect(url_for('main.index'))

@main_bp.route('/images/<folder_name>')
def get_images(folder_name):
    from . import mongo
    fs = GridFS(mongo.db)

    # Get pagination parameters
    page = int(request.args.get('page', 1))  # Default to page 1
    per_page = int(request.args.get('per_page', 20))  # Default to 10 items per page

    # Calculate the skip and limit values
    skip = (page - 1) * per_page
    limit = per_page

    # Find images by folder metadata
    total_files = mongo.db.fs.files.count_documents({'metadata.folder': folder_name})  # Get total number of files
    files = fs.find({'metadata.folder': folder_name}).skip(skip).limit(limit)

    image_list = [{'filename': file.filename, 'url': url_for('main.static_image', filename=file.filename)} for file in files]

    # Calculate total pages
    total_pages = (total_files + per_page - 1) // per_page  # Ceiling division for total pages

    return render_template('product_list.html', images=image_list, folder_name=folder_name, page=page, total_pages=total_pages)

@main_bp.route('/static/images/<filename>')
def static_image(filename):
    from . import mongo
    # Serve image files from GridFS
    fs = GridFS(mongo.db)
    file = fs.find_one({'filename': filename})
    if file:
        return send_file(file, mimetype='image/jpeg')
    print('File not found: {filename}')
    return "File not found", 404