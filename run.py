# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = None
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app():
    global app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hair_salon.db'

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes.auth import auth_bp
    from .routes.booking import booking_bp
    from .routes.store import store_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(store_bp)

    with app.app_context():
        db.create_all()

    return app

# app/models.py
from . import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    available_from = db.Column(db.Time, nullable=False)
    available_to = db.Column(db.Time, nullable=False)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Pending')
    total_price = db.Column(db.Float)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        user = User(username=username, email=email, password_hash=password)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('booking.dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# app/routes/booking.py
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from ..models import Staff, Service, Booking
from .. import db
from datetime import datetime, timedelta

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/')
def index():
    return render_template('index.html')

@booking_bp.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', bookings=bookings)

@booking_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    services = Service.query.all()
    staff = Staff.query.all()
    if request.method == 'POST':
        staff_id = request.form['staff']
        service_id = request.form['service']
        start = datetime.strptime(request.form['start'], '%Y-%m-%dT%H:%M')
        service = Service.query.get(service_id)
        end = start + timedelta(minutes=service.duration_minutes)
        # Check conflicts
        conflict = Booking.query.filter_by(staff_id=staff_id).filter(
            Booking.start_time < end, Booking.end_time > start).first()
        if conflict:
            return "Time slot is already booked"
        booking = Booking(user_id=current_user.id, staff_id=staff_id,
                          service_id=service_id, start_time=start, end_time=end)
        db.session.add(booking)
        db.session.commit()
        return redirect(url_for('booking.dashboard'))
    return render_template('book.html', services=services, staff=staff)

# app/routes/store.py
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from ..models import Product, CartItem, Order, OrderItem
from .. import db
from datetime import datetime

store_bp = Blueprint('store', __name__)

@store_bp.route('/store')
def store():
    products = Product.query.all()
    return render_template('store.html', products=products)

@store_bp.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in items)
    return render_template('cart.html', items=items, total=total)

@store_bp.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += 1
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(item)
    db.session.commit()
    return redirect(url_for('store.cart'))

@store_bp.route('/checkout')
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in items)
    order = Order(user_id=current_user.id, total_price=total, order_date=datetime.utcnow())
    db.session.add(order)
    db.session.flush()
    for item in items:
        order_item = OrderItem(order_id=order.id, product_id=item.product_id,
                               quantity=item.quantity,
                               subtotal=item.product.price * item.quantity)
        db.session.add(order_item)
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('booking.dashboard'))
