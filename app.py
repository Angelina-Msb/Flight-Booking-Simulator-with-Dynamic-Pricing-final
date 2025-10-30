from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import sys

# Assuming these are correct imports from your project:
from models import db, Flight, Booking, User
from pricing import calculate_dynamic_price 

from datetime import datetime, timedelta
import random
import string
import time
import locale 

# Set locale for INR formatting (for display in dictionaries)
try:
    locale.setlocale(locale.LC_MONETARY, 'en_IN.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_MONETARY, 'C') 

# Create the Flask app
app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flights.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key-for-ur-flight-mate'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# --- Initialization ---
db.init_app(app)
CORS(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Helper function to format INR cleanly (e.G., 1,00,000)
def format_inr(amount):
    """Formats an integer amount as Indian Rupee string (e.g., ₹1,00,000)"""
    return f"₹{int(amount):,}"


@jwt.user_identity_loader
def user_identity_lookup(user_object):
    """Called when token is created (identity=user). Returns the ID to store."""
    return user_object.id


# --- Helper Functions ---

def generate_pnr():
    """Generates a random 6-character PNR."""
    chars = string.ascii_uppercase + string.digits
    while True:
        pnr = ''.join(random.choice(chars) for _ in range(6))
        # Check if this PNR already exists
        if not Booking.query.filter_by(pnr=pnr).first():
            return pnr # Return the unique PNR

def flight_to_dict(flight):
    """Converts a Flight object to a dictionary for JSON response."""
    price_breakdown = calculate_dynamic_price(flight)
    final_price_raw = price_breakdown['final_price_inr']
    base_price_raw = price_breakdown['base_price_inr']
    
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time.isoformat(),
        "arrival_time": flight.arrival_time.isoformat(),
        "base_price_inr_formatted": format_inr(base_price_raw),
        "dynamic_price_formatted": format_inr(final_price_raw), 
        "base_price_inr_raw": base_price_raw, 
        "dynamic_price_raw": final_price_raw,
        "seats_available": flight.seats_available,
        "price_breakdown": {
            'base_price_inr': base_price_raw,
            'surcharges': price_breakdown['surcharges']
        }
    }

def booking_to_dict(booking):
    """Converts a Booking object to a dictionary for JSON response."""
    formatted_price_paid = format_inr(booking.price_paid)
    
    return {
        "pnr": booking.pnr,
        "status": booking.status,
        "passenger_name": booking.passenger_name,
        "passenger_email": booking.passenger_email,
        "price_paid": formatted_price_paid,
        "seat_number": booking.seat_number,
        "booking_time": booking.booking_time.isoformat(),
        "flight_number": booking.flight.flight_number,
        "origin": booking.flight.origin,
        "destination": booking.flight.destination,
        "departure_time": booking.flight.departure_time.isoformat(),
    }

def generate_and_add_flight(origin, destination, date_str):
    try:
        search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None 

    if search_date < datetime.now().date():
        search_date = datetime.now().date() + timedelta(days=1)
    
    dep_hour = random.randint(9, 17)
    dep_minute = random.choice([0, 30])
    departure_dt = datetime(search_date.year, search_date.month, search_date.day, dep_hour, dep_minute, 0)
    duration_hours = random.randint(3, 6)
    arrival_dt = departure_dt + timedelta(hours=duration_hours, minutes=random.randint(0, 59))
    base_price = round(200 + duration_hours * 50 + random.randint(10, 50), 2)
    total_seats = 150
    
    # FIX for unique flight number
    flight_num = f"{random.choice(['UR', 'FM', 'FL'])}{random.randint(100, 999)}"
    if Flight.query.filter_by(flight_number=flight_num).first():
        flight_num = f"{random.choice(['UR', 'FM', 'FL'])}{random.randint(1000, 9999)}"

    new_flight = Flight(
        flight_number=flight_num,
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
    return "Welcome to the Ur Flight Mate Simulator! API is running on port 5000."


@app.route('/api/flights/search', methods=['GET'])
def search_flights():
    try:
        origin = request.args.get('origin')
        destination = request.args.get('destination')
        date_str = request.args.get('date')
        
        if not all([origin, destination, date_str]):
            return jsonify({"error": "Missing required parameters"}), 400

        try:
            search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        query = Flight.query.filter(
            Flight.origin.ilike(f"%{origin}%"),
            Flight.destination.ilike(f"%{destination}%"),
            db.func.date(Flight.departure_time) == search_date
        )

        flights_list = query.order_by(Flight.base_price).all()

        if not flights_list:
            new_flight = generate_and_add_flight(origin, destination, date_str)
            if new_flight:
                flights_list.append(new_flight)
        
        if not flights_list:
             return jsonify({"message": "No flights found"}), 404

        results = [flight_to_dict(f) for f in flights_list]
        return jsonify(results), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


# --- Authentication Routes ---

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"error": "Missing name, email, or password"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User with this email already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, email=email, password_hash=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database integrity error (e.g., email exists)"}), 409
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
        access_token = create_access_token(identity=user)
        
        return jsonify({
            "access_token": access_token,
            "user": {"id": user.id, "name": user.name, "email": user.email}
        }), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401


# --- Booking Routes (FIXED logic is below) ---

@app.route('/api/bookings/create', methods=['POST'])
@jwt_required()
def create_booking():
    user_id = get_jwt_identity() 
    user = User.query.get(user_id) 

    if not user:
        return jsonify({"error": "User not found for this token. Please re-login."}), 401

    data = request.get_json()
    flight_id = data.get('flight_id')
    seat_number = data.get('seat_number')

    if not all([flight_id, seat_number]):
        return jsonify({"error": "Missing flight_id or seat_number"}), 400

    try:
        flight = Flight.query.get(flight_id)

        if not flight:
            return jsonify({"error": "Flight not found"}), 404
        
        if flight.seats_available <= 0:
            return jsonify({"error": "Flight is fully booked"}), 409

        flight.seats_available -= 1
        
        price_breakdown_data = calculate_dynamic_price(flight)
        final_price_raw = price_breakdown_data['final_price_inr'] 

        pnr_code = generate_pnr() # Now guaranteed to be unique
        
        new_booking = Booking(
            user_id=user.id,
            flight_id=flight_id,
            passenger_name=user.name,
            passenger_email=user.email,
            pnr=pnr_code,
            seat_number=seat_number,
            price_paid=final_price_raw, 
            status='CONFIRMED'
        )

        db.session.add(new_booking)
        db.session.commit()
        
        return jsonify({
            "message": "Booking successful!",
            "booking": booking_to_dict(new_booking)
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        print(f"\n--- DATABASE INTEGRITY FAILURE (Likely PNR collision) ---\n{e}\n", file=sys.stderr)
        return jsonify({"error": "Booking failed due to a database conflict. Please try again."}), 500
    except Exception as e:
        db.session.rollback()
        print(f"\n--- BOOKING TRANSACTION FAILED (Unknown Error) ---\n{e}\n", file=sys.stderr)
        return jsonify({"error": "Booking failed due to an internal server error."}), 500


@app.route('/api/bookings/my-bookings', methods=['GET'])
@jwt_required()
def get_user_bookings():
    user_id = get_jwt_identity()
    
    try:
        bookings = Booking.query.filter_by(user_id=user_id).all()
        
        if not bookings:
            return jsonify({"message": "No bookings found for this user."}), 200
        
        results = [booking_to_dict(b) for b in bookings]
        return jsonify(results), 200
    
    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route('/api/bookings/<pnr>', methods=['GET'])
@jwt_required()
def get_booking_by_pnr(pnr):
    user_id = get_jwt_identity()
    
    try:
        booking = Booking.query.filter_by(pnr=pnr, user_id=user_id).first()
        if not booking:
            return jsonify({"error": "Booking not found or access denied."}), 404
        return jsonify(booking_to_dict(booking)), 200
    
    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route('/api/bookings/<pnr>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(pnr):
    user_id = get_jwt_identity()

    try:
        booking = Booking.query.filter_by(pnr=pnr, user_id=user_id).first()

        if not booking:
            return jsonify({"error": "Booking not found or access denied."}), 404
        if booking.status == 'CANCELLED':
            return jsonify({"error": "Booking is already cancelled."}), 409
        
        flight = Flight.query.get(booking.flight_id)
        if not flight:
            return jsonify({"error": "Flight details missing for cancellation."}), 500

        booking.status = 'CANCELLED'
        flight.seats_available += 1
        db.session.commit()

        return jsonify({"message": "Booking successfully cancelled."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Cancellation failed: {str(e)}"}), 500


# --- Run App ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(debug=True, port=5000)