from bson.objectid import ObjectId
from collections import defaultdict
from datetime import datetime

def get_content_recommendations(user_id, db, exclude_ids=[], limit=5):
    # 1. Fetch user's active bookings
    user_bookings = list(db.bookings.find({"user_id": user_id, "status": "Active"}))
    
    # If they have no bookings, return empty (so the History row hides itself)
    if not user_bookings:
        return []

    booked_event_ids = [b['event_id'] for b in user_bookings]
    user_profile = defaultdict(float)

    # 2. Build profile based on what they actually paid for
    for booking in user_bookings:
        event = db.events.find_one({"_id": ObjectId(booking['event_id'])})
        if event and 'genre' in event:
            weight = booking.get('quantity', 1) 
            for genre in event['genre']:
                user_profile[genre] += weight

    # 3. Combine booked IDs and the already-showing Genre IDs to prevent repetition
    all_excluded = [ObjectId(eid) for eid in booked_event_ids] + exclude_ids
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    
    candidates = db.events.find({
        "_id": {"$nin": all_excluded},
        "available_seats": {"$gt": 0},
        "date_time": {"$gt": now_str}
    })

    # 4. Score Candidates against the User Profile
    scored_events = []
    for event in candidates:
        score = sum(user_profile.get(genre, 0.0) for genre in event.get('genre', []))
        if score > 0:
            final_score = score + (event.get('rating', 0) * 0.1)
            scored_events.append((final_score, event))

    scored_events.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_events[:limit]]