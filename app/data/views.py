import os
import json
from flask import render_template, abort
from . import data_bp

# Set the base directory for the project
base_dir = os.path.abspath(os.path.dirname(__file__))

# Helper function to load product data from the JSON file
def load_product_data():
    with open(os.path.join(base_dir, 'data', 'package.json'), 'r') as file:
        return json.load(file)

# Route for displaying the product detail
@data_bp.route('/product/<filename>')
def product_detail(filename):
    # Load the data from the JSON file
    data = load_product_data()

    # Find the product by filename
    product = next((item for item in data['products'] if item['filename'] == filename), None)

    # If the product doesn't exist, return a 404 error
    if product is None:
        abort(404)

    return render_template('product_detail.html', product=product, folder_name='products', page=1)
