# from flask import render_template, redirect, url_for, session, request, flash
# from flask_login import login_required
# from bson import ObjectId
# from . import cart_bp
# from . import mongo

# @cart_bp.route('/cart')
# @login_required
# def cart():
#     session['cart'] = cart_items
#     # Assuming the cart is stored in the session
#     cart_items = session.get('cart', [])
    
#     # Calculate the total amount
#     total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

#     return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

# # Route to add items to the cart
# @cart_bp.route('/add_to_cart/<product_id>', methods=['POST'])
# @login_required
# def add_to_cart(product_id):
#     product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
#     if not product:
#         flash('Product not found', 'danger')
#         return redirect(url_for('main.get_images', folder_name='products'))

#     # Get the quantity from the form
#     quantity = int(request.form.get('quantity', 1))

#     # Add the product to the cart (stored in the session)
#     cart = session.get('cart', [])
    
#     # Check if the product is already in the cart
#     for item in cart:
#         if item['_id'] == product['_id']:
#             item['quantity'] += quantity
#             break
#     else:
#         # Add new product to cart
#         cart.append({
#             '_id': str(product['_id']),
#             'name': product['name'],
#             'price': product['price'],
#             'quantity': quantity
#         })

#     # Save the cart back to the session
#     session['cart'] = cart

#     flash(f'{product["name"]} added to cart!', 'success')
#     return redirect(url_for('main.cart'))

# # Route to remove items from the cart
# @cart_bp.route('/remove_from_cart/<product_id>', methods=['POST'])
# @login_required
# def remove_from_cart(product_id):
#     cart = session.get('cart', [])
    
#     # Filter out the product from the cart
#     cart = [item for item in cart if item['_id'] != product_id]

#     # Save the updated cart back to the session
#     session['cart'] = cart

#     flash('Item removed from cart', 'success')
#     return redirect(url_for('main.cart'))

# # Checkout route
# @cart_bp.route('/checkout', methods=['POST'])
# @login_required
# def checkout():
#     # Process the checkout
#     cart = session.get('cart', [])
    
#     if not cart:
#         flash('Your cart is empty', 'danger')
#         return redirect(url_for('main.cart'))
    
#     # Here you can add the logic for payment processing, saving the order, etc.
#     session.pop('cart', None)  # Clear the cart after checkout
#     flash('Checkout successful! Thank you for your purchase.', 'success')
    
#     return redirect(url_for('main.get_images', folder_name='products'))