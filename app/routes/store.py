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