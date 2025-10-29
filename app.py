from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from models import db, Flight, Booking, User # <-- Updated: Import new models
from pricing import calculate_dynamic_price
from datetime import datetime, timedelta
import random
import string
import time # For the simulator

# Create the Flask app
app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flights.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key-for-ur-flight-mate' # Change this in a real app!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) # Tokens expire after 1 hour

# --- Initialization ---
db.init_app(app)
CORS(app) # Allow frontend (on port 5500) to talk to backend (on port 5000)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# --- FIX for "Subject must be a string" error ---
# This tells JWTManager how to get the user ID (the 'identity') for the token
@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id
# ---------------------------------------------------


# --- Helper Functions ---

def generate_pnr():
    """Generates a random 6-character PNR."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

def flight_to_dict(flight):
    """Converts a Flight object to a dictionary for JSON response."""
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time.isoformat(),
        "arrival_time": flight.arrival_time.isoformat(),
        "base_price": flight.base_price,
        "dynamic_price": calculate_dynamic_price(flight), # Dynamic price calculation here
        "seats_available": flight.seats_available
    }

def booking_to_dict(booking):
    """Converts a Booking object to a dictionary for JSON response."""
    return {
        "pnr": booking.pnr,
        "status": booking.status,
        "passenger_name": booking.passenger_name,
        "passenger_email": booking.passenger_email,
        "price_paid": booking.price_paid,
        "seat_number": booking.seat_number,
        "booking_time": booking.booking_time.isoformat(),
        
        # Flight details are included for context
        "flight_number": booking.flight.flight_number,
        "origin": booking.flight.origin,
        "destination": booking.flight.destination,
        "departure_time": booking.flight.departure_time.isoformat(),
    }

def generate_and_add_flight(origin, destination, date_str):
    """Generates a new, realistic flight and adds it to the database."""
    try:
        search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None # Invalid date format

    # Ensure the date is not in the past
    if search_date < datetime.now().date():
        search_date = datetime.now().date() + timedelta(days=1)
    
    # Simple logic for determining flight time/duration based on route
    # Time window for departure (e.g., 9 AM to 5 PM)
    dep_hour = random.randint(9, 17)
    dep_minute = random.choice([0, 30])
    
    departure_dt = datetime(search_date.year, search_date.month, search_date.day, dep_hour, dep_minute, 0)
    
    # Determine base duration (3 to 6 hours)
    duration_hours = random.randint(3, 6)
    arrival_dt = departure_dt + timedelta(hours=duration_hours, minutes=random.randint(0, 59))
    
    # Determine base price based on duration
    base_price = round(200 + duration_hours * 50 + random.randint(10, 50), 2)
    
    total_seats = 150 # Standard plane size
    
    new_flight = Flight(
        flight_number=f"{random.choice(['UR', 'FM', 'FL'])}{random.randint(100, 999)}",
        origin=origin,
        destination=destination,
        departure_time=departure_dt,
        arrival_time=arrival_dt,
        base_price=base_price,
        total_seats=total_seats,
        seats_available=total_seats
    )
    
    db.session.add(new_flight)
    db.session.commit()
    return new_flight


# --- Core Routes ---

@app.route('/')
def home():
    return "Welcome to the Ur Flight Mate Simulator!"


@app.route('/api/flights/search', methods=['GET'])
def search_flights():
    """
    API endpoint to search for flights. Auto-generates a flight if none is found.
    """
    try:
        origin = request.args.get('origin')
        destination = request.args.get('destination')
        date_str = request.args.get('date')
        
        if not all([origin, destination, date_str]):
            return jsonify({
                "error": "Missing required parameters: origin, destination, and date (YYYY-MM-DD)."
            }), 400

        try:
            search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

        # Build the database query
        query = Flight.query.filter(
            Flight.origin.ilike(f"%{origin}%"),
            Flight.destination.ilike(f"%{destination}%"),
            db.func.date(Flight.departure_time) == search_date
        )

        # Default sort by price
        query = query.order_by(Flight.base_price)
        flights_list = query.all()

        # --- NEW LOGIC: AUTO-GENERATE FLIGHT if none is found ---
        if not flights_list:
            # Generate one flight for this route and add it to the list
            new_flight = generate_and_add_flight(origin, destination, date_str)
            if new_flight:
                flights_list.append(new_flight)
        
        # --- Final formatting ---
        if not flights_list:
             return jsonify({"message": "No flights found, and auto-generation failed."}), 404

        results = [flight_to_dict(f) for f in flights_list]

        return jsonify(results), 200

    except Exception as e:
        # Rollback in case the flight generation failed
        db.session.rollback()
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


# --- Authentication Routes (New Milestone) ---

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"error": "Missing name, email, or password"}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User with this email already exists"}), 409

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Create the new user
    new_user = User(name=name, email=email, password_hash=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error during signup: {str(e)}"}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        # Create an access token using the user's ID as the identity
        access_token = create_access_token(identity=user)
        
        # Return the token and basic user info
        return jsonify({
            "access_token": access_token,
            "user": {"id": user.id, "name": user.name, "email": user.email}
        }), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401


# --- Booking Routes (Protected) ---

@app.route('/api/bookings/create', methods=['POST'])
@jwt_required()
def create_booking():
    # Get the user ID from the JWT token
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    data = request.get_json()
    flight_id = data.get('flight_id')
    seat_number = data.get('seat_number')

    if not all([flight_id, seat_number]):
        return jsonify({"error": "Missing flight_id or seat_number"}), 400

    # Ensure this entire operation is atomic (safe from concurrency issues)
    try:
        flight = Flight.query.get(flight_id)

        if not flight:
            return jsonify({"error": "Flight not found"}), 404
        
        if flight.seats_available <= 0:
            return jsonify({"error": "Flight is fully booked"}), 409 # Conflict

        # 1. Update the Flight's seat count
        flight.seats_available -= 1
        
        # 2. Calculate the final price (concurrency safety)
        final_price = calculate_dynamic_price(flight)

        # 3. Create the unique PNR
        pnr_code = generate_pnr()
        
        # 4. Create the Booking record
        new_booking = Booking(
            user_id=user.id, # Link the user ID
            flight_id=flight_id,
            passenger_name=user.name, # Use logged-in user's name
            passenger_email=user.email, # Use logged-in user's email
            pnr=pnr_code,
            seat_number=seat_number,
            price_paid=final_price,
            status='CONFIRMED'
        )

        db.session.add(new_booking)
        db.session.commit()
        
        return jsonify({
            "message": "Booking successful!",
            "booking": booking_to_dict(new_booking)
        }), 201

    except Exception as e:
        # If anything fails, rollback the entire transaction (including seat count change)
        db.session.rollback()
        return jsonify({"error": f"Booking failed due to a concurrency error or internal issue: {str(e)}"}), 500


@app.route('/api/bookings/my-bookings', methods=['GET'])
@jwt_required()
def get_user_bookings():
    """Retrieve all confirmed bookings for the logged-in user."""
    user_id = get_jwt_identity()
    
    try:
        bookings = Booking.query.filter_by(user_id=user_id).all()
        
        if not bookings:
            return jsonify({"message": "No bookings found for this user."}), 200 # 200 is fine for an empty list
        
        results = [booking_to_dict(b) for b in bookings]
        return jsonify(results), 200
    
    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route('/api/bookings/<pnr>', methods=['GET'])
@jwt_required()
def get_booking_by_pnr(pnr):
    """Retrieve a specific booking by PNR, ensuring it belongs to the logged-in user."""
    user_id = get_jwt_identity()
    
    try:
        booking = Booking.query.filter_by(pnr=pnr, user_id=user_id).first()

        if not booking:
            # Return 404/403: Booking not found or does not belong to user
            return jsonify({"error": "Booking not found or access denied."}), 404

        return jsonify(booking_to_dict(booking)), 200
    
    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route('/api/bookings/<pnr>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(pnr):
    """Cancels a booking, marks the status, and returns the seat to the flight."""
    user_id = get_jwt_identity()

    try:
        booking = Booking.query.filter_by(pnr=pnr, user_id=user_id).first()

        if not booking:
            return jsonify({"error": "Booking not found or access denied."}), 404

        if booking.status == 'CANCELLED':
            return jsonify({"error": "Booking is already cancelled."}), 409
        
        # Start Transaction
        flight = Flight.query.get(booking.flight_id)

        if not flight:
             # This should not happen, but prevents crash
            return jsonify({"error": "Flight details missing for cancellation."}), 500

        # 1. Update status
        booking.status = 'CANCELLED'
        
        # 2. Return the seat (concurrency safe)
        flight.seats_available += 1
        
        db.session.commit()

        return jsonify({
            "message": "Booking successfully cancelled.",
            "booking": booking_to_dict(booking)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Cancellation failed due to a concurrency error or internal issue: {str(e)}"}), 500


# --- Run App ---

if __name__ == '__main__':
    with app.app_context():
        # Ensure database and tables exist
        db.create_all()
    
    app.run(debug=True, port=5000)
