from flask import Blueprint, request, session, jsonify
from flask import render_template, redirect, url_for, request, flash, current_app, send_file
from flask_login import login_user, login_required, logout_user
import requests.exceptions
from .forms import Admin, RegistrationForm, LoginForm
from gridfs import GridFS
import os
from app import mongo, bcrypt, csrf
from app.models import User
from bson.objectid import ObjectId
import json
from dotenv import load_dotenv
import requests
import json
import base64
from datetime import datetime


load_dotenv()

main_bp = Blueprint('main', __name__)

fs = GridFS(mongo.db)


@main_bp.before_request
def ensure_cart_exists():
    if 'cart' not in session:
        session['cart'] = [] 

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
    products = mongo.db.products.find()

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


@main_bp.route('/add_to_cart', methods=['POST'])
@csrf.exempt
def add_to_cart():
    try:
        data = request.get_json()
        print('Received data', data)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        # Fetch the product from MongoDB using product_id
        product = fs.find_one({'_id': ObjectId(product_id)})

        if not product:
            return jsonify({'message': 'Product not found'}), 404

        # Load the description from the metadata field
        description_data = json.loads(product.description)
        
        # Extract necessary fields from the description
        product_name = description_data.get('name', 'No name available')
        product_price = description_data.get('price', 0.0)

        # Get the cart from session, or initialize it if empty
        cart = session.get('cart', [])

        # Check if the product is already in the cart
        found = False
        for item in cart:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                found = True
                break

        # If product is not in the cart, add it
        if not found:
            session['cart'].append({
                'product_id': product_id,
                'name': product_name,
                'price': product_price,
                'quantity': quantity,
                'url': url_for('main.static_image', filename=product.filename)
            })

        # Update the session cart
        session['cart'] = cart
        session.modified = True

        return jsonify({'message': 'Product added', 'cart_count': len(cart)}), 200

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 400

from bson.objectid import ObjectId

@main_bp.route('/cart')
@login_required
def view_cart():
    cart = session.get('cart', [])
    total_price = 0

    for item in cart:
        product_id = item['product_id']
        
        # Fetch the product from MongoDB using ObjectId
        product = mongo.db.user.find_one({"_id": ObjectId(product_id)})

        # Set the item price based on the product retrieved or use default of 10
        item_price = product['price'] if product and 'price' in product else 10  # Default price of 10
        item['price'] = item_price  # Set price for rendering
        total_price += item_price * item['quantity']

    return render_template('cart.html', cart_items=cart, total_amount=total_price)

@main_bp.route('/remove_from_cart/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    # Get the cart from the session
    cart = session.get('cart', [])
    
    # Filter out the item with the given product_id
    updated_cart = [item for item in cart if item['product_id'] != product_id]
    
    # Update the session cart
    session['cart'] = updated_cart
    
    # Redirect back to the cart page
    return redirect(url_for('main.view_cart'))


@main_bp.route('/reset_cart', methods=['POST'])
def reset_cart():
    session.pop('cart', None)
    flash('Your cart has been reset.')
    return redirect(url_for('main.view_cart'))


@main_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = session.get('cart', [])
    total_amount = sum(item.get('price', 10) * item['quantity'] for item in cart)
    
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        address = request.form.get("address")
        city = request.form.get("city")
        zipcode = request.form.get("zipcode")
        paymentmethod = request.form.get("paymentMethod")
        cardnumber = request.form.get('cardnumber')
        expdate = request.form.get('expdate')
        cvv = request.form.get('cvv')
        mpesa_number = request.form.get('mpesa_number')
        paymentmethod = request.form.get('paypalmethod')
        crypto_address = request.form.get('crypto_address')
        amount = request.form.get("amount", 1)

        mongo.db.checkout_infor.insert_one(
            {
                "Email": email,
                "Usernane": username,
                "Address": address,
                "City": city,
                "Zipcode": zipcode,
                "Paymentmethod": paymentmethod,
                "Cardnumber": cardnumber,
                "Expdate": expdate,
                "Cvv": cvv,
                "Mpesa": mpesa_number,
                "Crypto_address": crypto_address,
                "Amount": amount
            }
        )

    return render_template('checkout.html', cart=cart, total_amoun=total_amount)


def get_access_token():
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    auth = base64.b64encode(f"{consumer_key}: {consumer_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def initiate_Stk_push(phone, amount):
    access_token = get_access_token()
    if "error" in access_token:
        return jsonify(access_token), 500
    
    passkey = ""
    bussiness_short_code = "174379"
    process_request_url = ""
    callback_url = "https://donplackerr.tech/success"
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((bussiness_short_code + passkey + timestamp).encode()).decode()

    stk_push_headers = {
        'Content-Type': 'application/json',
        "Authorization": f'Bearer {access_token}'
    }

    stk_push_payload = {
        "BusinessShortCode": bussiness_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": 'CustomerPayBillOnline',
        "Amount": amount,
        "PartyA": phone,
        "PartyB": bussiness_short_code,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "TONY OPEN SOURCE",
        "TransactionDesc": "STK Push payment"
    }
    try:
        response = requests.post(process_request_url, headers=stk_push_headers, json=stk_push_payload)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("ResponseCode") == "0":
            return jsonify(
                {
                    "CheckoutRequestID": response_data['CheckoutRequestID'],
                    "ResponseCode": response_data["ResponseCode"],
                    "CustomerMessage": response_data["CustomerMessage"]
                }
            )
        else:
            return jsonify({"error": 'STK push failed.'}), 400
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route('/success', methods=["POST"])
@login_required
def confirm():
    mpesa_number = request.form.get('mpesa_number')
    amount = request.form.get('amount', 1)
    return initiate_Stk_push(mpesa_number, amount)