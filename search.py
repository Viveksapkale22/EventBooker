from flask import Blueprint, render_template, request
from bson.objectid import ObjectId
from datetime import datetime

# Define the Blueprint
search_bp = Blueprint('search', __name__)

def get_db():
    from app import db
    return db

@search_bp.route('/search')
def search_events():
    # 1. Get the filter parameters from the URL
    query_text = request.args.get('q', '').strip()
    selected_genre = request.args.get('genre', '').strip()
    selected_city = request.args.get('city', '').strip()

    # 2. Base Query: Only show events happening in the future
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    mongo_query = {"date_time": {"$gt": now_str}}

    # 3. Add filters if the user provided them
    if query_text:
        # Case-insensitive search in the event name
        mongo_query["name"] = {"$regex": query_text, "$options": "i"}
    
    if selected_genre:
        mongo_query["genre"] = selected_genre
        
    if selected_city:
        mongo_query["city"] = selected_city

    # 4. Fetch the results from the database
    results = list(get_db().events.find(mongo_query).sort("date_time", 1))

    # 5. Data for our clickable filter buttons
    genres = ["Technology", "Music", "Food & Cooking", "Business & Startup", "Sports", "Art & Culture"]
    cities = ["Mumbai", "Palghar", "Thane", "Pune"]

    return render_template(
        'search.html', 
        events=results, 
        genres=genres, 
        cities=cities,
        current_q=query_text,
        current_genre=selected_genre,
        current_city=selected_city
    )