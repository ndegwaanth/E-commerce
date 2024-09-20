from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from . import admin_bp
from app import mongo
from bson.objectid import ObjectId
from gridfs import GridFS
from .form import Admin
import os


@admin_bp.route('/tony', methods=['POST'])
def admin_login():
    from . import mongo
    from app import mongo, bcrypt

    form = Admin()
    admin_email = os.getenv('EMAIL')
    admin_pass = os.getenv("PASSWORD")

    if form.validate_on_submit() and request.method == "POST":
        email = form.email.data
        password = form.password.data

        hash_admin_pass = bcrypt.generate_password_hash(password).decode('utf-8')
        mongo.db.admin.insert_one({"Email":email, "Password": hash_admin_pass})

        if admin_email == email and admin_pass == password:
            return render_template('admin_dashboard.html')
        else:
            return redirect(url_for('admin_bp.admin_login'))
    else:
        return "No templates"


@admin_bp.route('/dashboard')
def admin_dashboard():
    fs = GridFS(mongo.db)

    # Fetch images with metadata from GridFS
    images = []
    for file in fs.find():
        images.append({
            'filename': file.filename,
            'description': file.metadata.get('description', 'No description'),
            'folder': file.metadata.get('folder', 'products'),
            'url': url_for('admin.get_image', filename=file.filename)
        })

    # Fetch users
    users = mongo.db.users.find()

    return render_template('admin_dashboard.html', images=images, users=users)

@admin_bp.route('/delete_image/<filename>', methods=['POST'])
def delete_image(filename):
    fs = GridFS(mongo.db)
    file = fs.find_one({'filename': filename})
    if file:
        fs.delete(file._id)
        flash(f'Image {filename} has been deleted.')
    else:
        flash(f'Image {filename} not found.')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    mongo.db.users.delete_one({'_id': ObjectId(user_id)})
    flash(f'User with ID {user_id} has been deleted.')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/get_image/<filename>')
def get_image(filename):
    fs = GridFS(mongo.db)
    file = fs.find_one({'filename': filename})
    if file:
        return file.read(), 200, {'Content-Type': file.content_type}
    return 'Image not found', 404
