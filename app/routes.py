import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from .models import db, User, Location, Review
from datetime import datetime

main = Blueprint('main', __name__)

UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password')
            return redirect(url_for('main.login'))

        login_user(user)
        return redirect(url_for('main.dashboard'))

    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists')
            return redirect(url_for('main.register'))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            role='user'
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main.login'))

    return render_template('register.html')

@main.route('/dashboard')
@login_required
def dashboard():
    google_maps_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    locations = Location.query.all()
    locations_data = [{
        'id': loc.id,
        'name': loc.name,
        'latitude': loc.latitude,
        'longitude': loc.longitude,
        'user': loc.user.name
    } for loc in locations]
    return render_template('dashboard.html',
                         google_maps_key=google_maps_key,
                         locations=locations_data)

@main.route('/add_location', methods=['POST'])
@login_required
def add_location():
    data = request.get_json()
    new_location = Location(
        user_id=current_user.id,
        name=data.get('name'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    db.session.add(new_location)
    db.session.commit()
    return jsonify({'success': True, 'id': new_location.id})

@main.route('/location/<int:location_id>')
@login_required
def location_detail(location_id):
    location = Location.query.get_or_404(location_id)
    reviews = Review.query.filter_by(location_id=location_id).all()
    return render_template('location.html', location=location, reviews=reviews)

@main.route('/add_review/<int:location_id>', methods=['POST'])
@login_required
def add_review(location_id):
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    date_of_visit = request.form.get('date_of_visit')
    photo = request.files.get('photo')

    photo_filename = None
    if photo and allowed_file(photo.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(UPLOAD_FOLDER, filename))
        photo_filename = filename

    new_review = Review(
        location_id=location_id,
        user_id=current_user.id,
        rating=int(rating),
        comment=comment,
        date_of_visit=datetime.strptime(date_of_visit, '%Y-%m-%d').date() if date_of_visit else None,
        photo=photo_filename
    )
    db.session.add(new_review)
    db.session.commit()
    return redirect(url_for('main.location_detail', location_id=location_id))

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))