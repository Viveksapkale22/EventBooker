from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

# Define the Blueprint
auth_bp = Blueprint('auth', __name__)

# Helper to grab the database instance from app.py
def get_db():
    from app import db
    return db

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        genres = request.form.getlist('genre')

        if not genres:
            flash("Please select at least one favorite genre.", "danger")
            return redirect(url_for('auth.register'))

        if get_db().users.find_one({"email": email}):
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for('auth.login'))

        get_db().users.insert_one({
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "favorite_genres": genres,
            "created_at": datetime.now()
        })
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('auth.login'))

    genres_list = ["Technology", "Business & Startup", "Music", "Dance", "Sports", "Health & Fitness", "Art & Culture", "Food & Cooking", "Gaming", "Social & Community"]
    return render_template('register.html', genres=genres_list)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = get_db().users.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@auth_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = get_db().users.find_one({"_id": ObjectId(session['user_id'])})
    bookings = list(get_db().bookings.find({"user_id": session['user_id']}).sort("booking_date", -1))

    now = datetime.now()
    for b in bookings:
        try:
            event_date = datetime.strptime(b['event_date'], '%Y-%m-%dT%H:%M')
            time_difference = (event_date - now).total_seconds()
            
            # 24 hour cancellation rule (86400 seconds)
            b['can_cancel'] = True if (b['status'] == 'Active' and time_difference > 86400) else False
        except:
             b['can_cancel'] = False

    return render_template('profile.html', user=user, bookings=bookings)






# --- NEW: Checkout Page Route ---
@auth_bp.route('/checkout/<event_id>')
def checkout(event_id):
    if 'user_id' not in session:
        flash("Please login to book tickets.", "warning")
        return redirect(url_for('auth.login'))

    event = get_db().events.find_one({"_id": ObjectId(event_id)})
    if not event or event['available_seats'] <= 0:
        flash("Sorry, this event is unavailable or sold out.", "danger")
        return redirect(url_for('index'))

    return render_template('checkout.html', event=event)

# --- UPDATED: Booking Logic (Handles Quantity & Price) ---
@auth_bp.route('/book/<event_id>', methods=['POST'])
def book_event(event_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Get the number of tickets the user selected (default to 1 if missing)
    quantity = int(request.form.get('quantity', 1))
    
    event = get_db().events.find_one({"_id": ObjectId(event_id)})
    
    # Check if there are enough seats left!
    if not event or event['available_seats'] < quantity:
        flash(f"Booking failed: Only {event['available_seats']} seats available.", "danger")
        return redirect(url_for('auth.checkout', event_id=event_id))

    total_price = event['price'] * quantity

    # Deduct the exact number of seats selected
    get_db().events.update_one({"_id": ObjectId(event_id)}, {"$inc": {"available_seats": -quantity}})

    # Record the booking with quantity and total price
    booking = {
        "user_id": session['user_id'],
        "event_id": str(event['_id']),
        "event_name": event['name'],
        "event_date": event['date_time'],
        "image_url": event.get('image_url'),
        "quantity": quantity,                 # NEW
        "total_price": total_price,           # NEW
        "booking_date": datetime.now(),
        "status": "Active" 
    }
    get_db().bookings.insert_one(booking)
    
    flash(f"Success! You booked {quantity} ticket(s) for ₹{total_price}.", "success")
    return redirect(url_for('auth.profile'))

# --- UPDATED: Cancel Logic (Restores the correct number of seats) ---
@auth_bp.route('/cancel/<booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    booking = get_db().bookings.find_one({"_id": ObjectId(booking_id), "user_id": session['user_id']})
    if booking and booking['status'] == 'Active':
        # Add the EXACT quantity of seats back to the event pool
        seats_to_restore = booking.get('quantity', 1) 
        get_db().events.update_one({"_id": ObjectId(booking['event_id'])}, {"$inc": {"available_seats": seats_to_restore}})
        
        get_db().bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "Cancelled"}})
        flash("Your booking has been cancelled and your seats have been released.", "success")
    
    return redirect(url_for('auth.profile'))