from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson.objectid import ObjectId
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def get_db():
    from app import db  
    return db.events

# --- SECURITY: The "Bouncer" ---
@admin_bp.before_request
def require_login():
    # If they are trying to access any admin route EXCEPT the login page...
    if request.endpoint != 'admin.login':
        # ...check if they are logged in. If not, kick them to the login screen!
        if not session.get('logged_in'):
            return redirect(url_for('admin.login'))

# --- NEW: Login Route ---
@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hardcoded credentials for your Demo
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid username or password!", "danger")
            
    return render_template('admin/login.html')

# --- NEW: Logout Route ---
@admin_bp.route('/admin/logout')
def logout():
    session.clear() # Destroys the login session
    return redirect(url_for('index')) # Sends them back to the main website


@admin_bp.route('/admin')
def dashboard():
    events = list(get_db().find().sort("created_at", -1))
    return render_template('admin/dashboard.html', events=events)

@admin_bp.route('/admin/event/new', methods=['GET', 'POST'])
@admin_bp.route('/admin/event/edit/<id>', methods=['GET', 'POST'])
def manage_event(id=None):
    event = None
    if id:
        event = get_db().find_one({"_id": ObjectId(id)})

    if request.method == 'POST':
        event_data = {
            "name": request.form.get('name'),
            "description": request.form.get('description'),
            "genre": request.form.getlist('genre'),
            
            # --- NEW: Location Dropdowns ---
            "state": request.form.get('state'),
            "city": request.form.get('city'),
            "area": request.form.get('area'),
            "location": request.form.get('location'), # Specific Venue Name
            
            # --- NEW: Perfect Date/Time & Rating ---
            "date_time": request.form.get('date_time'), # Now comes as YYYY-MM-DDTHH:MM
            "duration": request.form.get('duration'),
            "rating": float(request.form.get('rating') or 0.0), 
            
            "total_seats": int(request.form.get('total_seats') or 0),
            "price": float(request.form.get('price') or 0.0),
            "organizer_name": request.form.get('organizer_name'),
            "contact_email": request.form.get('contact_email'),
            "image_url": request.form.get('image_url')
        }

        if id:
            get_db().update_one({"_id": ObjectId(id)}, {"$set": event_data})
        else:
            event_data["available_seats"] = event_data["total_seats"]
            event_data["popularity"] = 0
            event_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            get_db().insert_one(event_data)
        
        return redirect(url_for('admin.dashboard'))

    # Dropdown Data for the Demo
    dropdown_data = {
        "states": ["Maharashtra", "Goa", "Gujarat", "Delhi"],
        "cities": ["Mumbai", "Palghar", "Thane", "Pune", "Navi Mumbai"],
        "areas": ["Virar West", "Virar East", "Vasai", "Nalasopara", "Andheri", "Bandra", "South Mumbai"],
        "genres": ["Technology", "Business & Startup", "Education & Workshop", "Music", "Dance", "Sports", "Health & Fitness", "Art & Culture", "Networking", "Food & Cooking", "Gaming", "Social & Community"]
    }
    
    return render_template('admin/event_form.html', event=event, data=dropdown_data)

@admin_bp.route('/admin/delete/<id>')
def delete_event(id):
    get_db().delete_one({"_id": ObjectId(id)})
    return redirect(url_for('admin.dashboard'))