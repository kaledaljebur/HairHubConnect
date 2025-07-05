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