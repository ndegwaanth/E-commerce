from flask import Blueprint, request, session
from flask import render_template, redirect, url_for, request, flash, current_app, send_file
from flask_login import login_user, login_required, logout_user
from .forms import Admin, RegistrationForm, LoginForm
from gridfs import GridFS
import os
from . import mongo
from app import mongo, bcrypt
from app.models import User
from bson.objectid import ObjectId
import json
from dotenv import load_dotenv

load_dotenv()

main_bp = Blueprint('main', __name__)

fs = GridFS(mongo.db)

@main_bp.route('/')
def index():
    return render_template('homepage.html')


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    from .models import User

    form = RegistrationForm()
    if form.validate_on_submit():
        if form.password.data == form.confirm_password.data:
            username = form.username.data
            email = form.email.data
            password = form.password.data
            hashed_password = bcrypt.generate_password_hash(password).decode('utf8')

            # Insert user into the database
            mongo.db.users.insert_one({'Username': username, 'Email': email, 'Password': hashed_password})
            
            # Create a user object and log them in
            user_dict = mongo.db.users.find_one({'Email': email})
            user = User(user_dict)
            login_user(user)

            flash(f'Account created for {username}!', 'success')
            return redirect(url_for('main.get_images', folder_name='products'))
        else:
            flash('Passwords do not match!', 'danger')
    return render_template('register.html', form=form)


@main_bp.route('/home', methods=['GET'])
def home():
    images = ['url_for(main.get_images)']
    folder_name = 'products'
    page = 1
    total_pages = 7

    return render_template('product_list.html', images=images, folder_name=folder_name, page=page, total_pages=total_pages)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user_dict = mongo.db.users.find_one({'Email': email})

        if user_dict:
            # Check password hash
            if bcrypt.check_password_hash(user_dict['Password'], password):
                user = User(user_dict)
                login_user(user)
                return redirect(url_for('main.get_images', folder_name='products'))
            else:
                return 'Incorrect password. Please try again.', 'danger'
        else:
            return redirect(url_for('main.register'))
    else:
        return render_template('login.html', form=form)

@main_bp.route('/admin/dashboard')
@login_required
def admin():
    return render_template('admin_dashboard.html')


@main_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = Admin()

    # Admin credentials stored in environment variables
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_pass = os.getenv('ADMIN_PASSWORD')

    if form.validate_on_submit() and request.method == 'POST':
        email = form.email.data
        password = form.password.data

        # Check if the provided email matches the admin email
        if email == admin_email:
            # Check if the provided password matches the hashed admin password
            if bcrypt.check_password_hash(admin_pass, password):
                # If credentials are correct, set session
                session['admin_logged_in'] = True
                session['admin_email'] = email

                # Redirect to the admin dashboard
                return redirect(url_for('main.admin'))
            else:
                flash("Invalid password. Please try again.", "danger")
        else:
            flash("Invalid email. Please try again.", "danger")
    
    return render_template('admin_login.html', form=form)


@main_bp.route('/upload-images')
def upload_images():
    images_path = os.path.join(current_app.root_path, 'static/images')

    # Fetch all products from MongoDB
    products = mongo.db.products.find()  # Assuming `products` collection contains product metadata

    # Create a dictionary to quickly access product metadata by filename
    product_metadata = {}
    for product in products:
        product_metadata[product['filename']] = {
            'name': product.get('name', 'No name available'),
            'description': product.get('description', 'No description available'),
            'price': product.get('price', 'N/A'),
            'inStock': product.get('inStock', False)
        }

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
                continue

            # Fetch the metadata for the current file
            metadata = product_metadata.get(file_name, {
                "name": "Sample Product",
                "description": "Sample product description.",
                "price": 10.99,
                "inStock": True
            })

            # Open and upload the file to GridFS with folder and product metadata
            with open(file_path, 'rb') as f:
                fs.put(f, filename=file_name, metadata={
                    'folder': folder_name,
                    'description': json.dumps(metadata)  # Store metadata as a JSON string
                })

    flash('All images have been uploaded successfully.')
    return redirect(url_for('main.index'))

@main_bp.route('/images/<folder_name>', methods=['GET'])
@login_required
def get_images(folder_name):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search_query = request.args.get('search', '')

    skip = (page - 1) * per_page
    limit = per_page

    # Build the query to search images
    query = {'metadata.folder': folder_name}
    if search_query:
        query['filename'] = {'$regex': search_query, '$options': 'i'}  # Case-insensitive search

    # Find images based on the query
    total_files = mongo.db.fs.files.count_documents(query)
    files = fs.find(query).skip(skip).limit(limit)

    image_list = []
    for file in files:
        # Access the description field if it exists
        description_data = getattr(file, 'description', None)
        if description_data:
            try:
                description = json.loads(description_data)
            except json.JSONDecodeError:
                description = {"description": "No valid description available."}
        else:
            description = {"description": "No description available."}

        # Append the necessary data to the image list
        image_list.append({
            '_id': str(file._id),  # Ensure _id is in string format
            'filename': file.filename,
            'url': url_for('main.static_image', filename=file.filename),
            'description': description.get('description', 'No description available'),
            'name': description.get('name', 'No name available'),
            'price': description.get('price', 'N/A'),
            'inStock': description.get('inStock', False)
        })

    # Calculate total pages
    total_pages = (total_files + per_page - 1) // per_page

    return render_template('product_list.html', images=image_list, folder_name=folder_name, page=page, total_pages=total_pages)


@main_bp.route('/static/images/<filename>')
def static_image(filename):
    
    file = fs.find_one({'filename': filename})
    if file:
        return send_file(file, mimetype='image/jpeg')
    print(f'File not found: {filename}')
    return redirect(url_for('main.home'))

@main_bp.route('/products/<product_id>', methods=['GET'])
@login_required
def product_detail(product_id):
    try:
        # Fetch the product using its _id from GridFS
        file = fs.get(ObjectId(product_id))
    except Exception as e:
        print(f"Error fetching file: {e}")
        return "Product not found", 404

    if file:
        # Extract description data and clean it
        description_data = file.description
        print(f"Raw description data: {description_data}")

        # Clean the description_data to remove unwanted characters
        description_data_cleaned = description_data.replace('\n', '').strip()
        print(f"Cleaned description data: {description_data_cleaned}")

        try:
            description = json.loads(description_data_cleaned)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            description = {
                "name": "No name available",
                "description": "No description available",
                "price": "N/A",
                "inStock": False
            }

        # Prepare the product data to pass to the template
        image = {
            '_id': str(file._id),
            'filename': file.filename,
            'name': description.get('name', 'No name available'),
            'description': description.get('description', 'No description available'),
            'price': description.get('price', 'N/A'),
            'inStock': description.get('inStock', False),
            'url': url_for('main.static_image', filename=file.filename),
        }

        print(f"Image data: {image}")

        folder_name = file.metadata.get('folder', 'products')
        return render_template('product_detail.html', image=image, folder_name=folder_name)

    return "Product not found", 404



@main_bp.route('/products', methods=['GET'])
def product_list():
    # Fetch the list of images from the database (MongoDB/GridFS)
    images = []
    files = fs.find({})  # Assuming you're retrieving the files from GridFS

    for file in files:
        description_data = file.metadata.get('description', '{}')
        try:
            description = json.loads(description_data)
        except json.JSONDecodeError:
            description = {}

        image = {
            '_id': str(file._id),  # Convert ObjectId to string
            'name': description.get('name', 'No name available'),
            'description': description.get('description', 'No description available'),
            'price': description.get('price', 'N/A'),
            'url': url_for('main.static_image', filename=file.filename)
        }
        images.append(image)

    return render_template('product_list.html', images=images)


@main_bp.route('/facebook-login')
def facebook_login():
    # Implement Facebook OAuth login
    pass

@main_bp.route('/google-login')
def google_login():
    # Implement Google OAuth login
    pass


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))


# @main_bp.route('/add_to_cart/<product_id>', methods=['POST'])
# @login_required
# def add_to_cart(product_id):
#     # Fetch the product from GridFS
#     product = fs.get(ObjectId(product_id))  # Use fs.get to retrieve the GridOut object

#     if not product or 'price' not in product:
#         flash('Product not found.', 'danger')
#         return redirect(url_for('main.get_images'))

#     # Access product metadata
#     product_metadata = product.metadata

#     # Ensure the necessary fields exist in the metadata
#     if not all(key in product_metadata for key in ['name', 'price']):
#         flash('Product data is incomplete.', 'danger')
#         return redirect(url_for('main.get_images', folder_name='products'))

#     # Get the current cart from the session
#     cart = session.get('cart', [])

#     # Add the product to the cart
#     cart.append({
#         'product_id': str(product._id),  # Use the _id of the product
#         'name': product_metadata['name'],  # Access the name from the metadata
#         'price': product_metadata['price'],  # Access the price from the metadata
#         'quantity': int(request.form.get('quantity', 1))  # Get the quantity from the form
#     })

#     # Save the updated cart back to the session
#     session['cart'] = cart
#     flash(f"{product_metadata['name']} added to cart!", 'success')
    
#     return redirect(url_for('main.get_images', folder_name='products'))

@main_bp.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    print("Received product ID:", product_id)

    try:
        # Fetch the product from GridFS
        grid_out = fs.get(ObjectId(product_id))
        print("Fetched product:", grid_out)

        # Access the 'description' field directly (as a string)
        product_description = grid_out.description
        print("Product Description:", product_description)

        # Parse the 'description' field (it's a JSON string)
        product_details = json.loads(product_description)
        print("Parsed product details:", product_details)

        # Ensure the product has a 'price'
        if 'price' not in product_details:
            return "Product is missing price", 400

        # Get the current cart from the session
        cart = session.get('cart', [])

        # Check if the product is already in the cart and update its quantity
        for item in cart:
            if item['_id'] == product_id:  # Use product_id as the identifier
                item['quantity'] += int(request.form.get('quantity', 1))
                break
        else:
            # If the product is not already in the cart, add it
            cart.append({
                '_id': product_id,  # Use the product_id from the URL/GridFS
                'name': product_details['name'],
                'price': product_details['price'],  # Add the parsed price
                'quantity': int(request.form.get('quantity', 1))
            })

        # Update the cart in the session
        session['cart'] = cart

        return "Product added to cart", 200

    except Exception as e:
        print("Error:", e)
        return "An error occurred", 500


@main_bp.route('/cart')
@login_required
def view_cart():
    # Get the cart from the session or an empty list if the cart is not present
    cart = session.get('cart', [])

    # Safeguard: use get() method to ensure that if 'price' or 'quantity' is missing, it defaults to 0
    total_price = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart)

    # Render the cart template with cart items and total amount
    return render_template('cart.html', cart_items=cart, total_amount=total_price)


# Route to clear the cart
@main_bp.route('/clear_cart')
@login_required
def clear_cart():
    session.pop('cart', None)
    flash('Cart cleared!', 'success')
    return redirect(url_for('main.view_cart'))

@main_bp.route('/remove_from_cart/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['product_id'] != product_id]  # Remove item by product_id
    session['cart'] = cart
    flash('Item removed from cart!', 'success')
    return redirect(url_for('main.view_cart'))

@main_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    return render_template('checkout.html')