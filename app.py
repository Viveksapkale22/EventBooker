from flask import Flask, render_template, session, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

from admin import admin_bp
from auth import auth_bp

# NEW: Import our recommendation engine!
from rs_con import get_content_recommendations
from search import search_bp

app = Flask(__name__)
app.secret_key = "demo_secret"

# ⚠️ Remember to use your NEW password here once you change it in Atlas!
MONGO_URI = "mongodb+srv://viveksapkale0022_db_user:ldvBxaR6509CEkBG@cluster0.hgkqkwy.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.event_db 

app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(search_bp)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user = db.users.find_one({"_id": ObjectId(session['user_id'])})
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")

    # --- TIER 1: Match from Registration Profile Genres (Top 5) ---
    genre_events = []
    genre_ids = []
    if user and 'favorite_genres' in user:
        genre_events = list(db.events.find({
            "genre": {"$in": user['favorite_genres']},
            "available_seats": {"$gt": 0},
            "date_time": {"$gt": now_str}
        }).sort("rating", -1).limit(5))
        genre_ids = [e['_id'] for e in genre_events]

    # --- TIER 2: Match from Past Bookings via rs_con (Top 5) ---
    # We pass 'genre_ids' so the AI knows to ignore the events already shown in Tier 1!
    history_events = get_content_recommendations(session['user_id'], db, exclude_ids=genre_ids, limit=5)
    history_ids = [e['_id'] for e in history_events]

    # --- TIER 3: All Remaining Events ---
    # We combine Tier 1 and Tier 2 IDs to completely exclude them from the bottom list
    all_excluded_ids = genre_ids + history_ids
    
    other_events = list(db.events.find({
        "_id": {"$nin": all_excluded_ids},
        "date_time": {"$gt": now_str}
    }).sort("created_at", -1).limit(15))

    # Pass all 3 distinct lists to the HTML
    return render_template('index.html', 
                           genre_events=genre_events, 
                           history_events=history_events, 
                           events=other_events)

if __name__ == "__main__":
    app.run(debug=True)