from flask import Flask, jsonify, request
# --- NEW IMPORTS ---
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
# --- UPDATED MODEL IMPORT ---
from models import db, Flight, Booking, User
from datetime import datetime, timedelta
from pricing import calculate_dynamic_price
from flask_cors import CORS
import random
import string

# 1. Create the Flask app
app = Flask(__name__)
# Add CORS support
CORS(app)

# 2. Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flights.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 3. NEW: Configure Security ---
# A secret key for JWT (change this in production)
app.config["JWT_SECRET_KEY"] = "your-super-secret-key-for-jwt"
# Initialize extensions
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# 4. Initialize the database with our app
db.init_app(app)

# 5. A simple 'test route'
@app.route('/')
def home():
    return "Welcome to the Ur Flight Mate Simulator!"

# --- Helper Function ---
def generate_pnr():
    """Generates a unique 6-character PNR."""
    while True:
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing = Booking.query.filter_by(pnr=pnr).first()
        if not existing:
            return pnr

# --- 6. NEW: AUTHENTICATION API ENDPOINTS ---

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """API endpoint for user registration."""
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({"error": "Missing name, email, or password"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({"error": "Email already exists"}), 409 # 409 = Conflict

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # Create new user
    new_user = User(
        email=data['email'],
        name=data['name'],
        password_hash=hashed_password
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """API endpoint for user login."""
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=data['email']).first()

    # Check if user exists and password is correct
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        # Create a new token
        access_token = create_access_token(identity=user.id)
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401 # 401 = Unauthorized

# --- 7. FLIGHT SEARCH API (Unchanged) ---
# This remains public, anyone can search flights.

@app.route('/api/flights', methods=['GET'])
def get_all_flights():
    try:
        flights_list = Flight.query.all()
        results = []
        for flight in flights_list:
            current_price = calculate_dynamic_price(flight)
            results.append({
                "id": flight.id, "flight_number": flight.flight_number, "origin": flight.origin,
                "destination": flight.destination, "departure_time": flight.departure_time.isoformat(),
                "arrival_time": flight.arrival_time.isoformat(), "base_price": flight.base_price,
                "dynamic_price": current_price, "seats_available": flight.seats_available
            })
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/flights/search', methods=['GET'])
def search_flights():
    try:
        origin = request.args.get('origin')
        destination = request.args.get('destination')
        date_str = request.args.get('date')
        if not all([origin, destination, date_str]):
            return jsonify({"error": "Missing required parameters."}), 400
        search_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        query = Flight.query.filter(
            Flight.origin.ilike(f"%{origin}%"),
            Flight.destination.ilike(f"%{destination}%"),
            db.func.date(Flight.departure_time) == search_date
        )
        sort_by = request.args.get('sort_by', 'price')
        if sort_by == 'duration':
            query = query.order_by(Flight.arrival_time - Flight.departure_time)
        else:
            query = query.order_by(Flight.base_price)

        flights_list = query.all()

        if not flights_list and origin and destination and search_date:
            try:
                departure_time = datetime.combine(search_date, datetime.min.time()) + timedelta(hours=random.randint(8, 20), minutes=random.choice([0, 15, 30, 45]))
                arrival_time = departure_time + timedelta(hours=random.randint(2, 6), minutes=random.randint(0, 59))
                new_flight = Flight(
                    flight_number=''.join(random.choices(string.ascii_uppercase, k=2)) + str(random.randint(100, 999)),
                    origin=origin, destination=destination, departure_time=departure_time,
                    arrival_time=arrival_time, base_price=round(random.uniform(150.0, 450.0), 2),
                    total_seats=random.choice([120, 150, 180]), seats_available=random.choice([120, 150, 180])
                )
                db.session.add(new_flight)
                db.session.commit()
                flights_list = [new_flight]
            except Exception as e:
                db.session.rollback()
                return jsonify({"error": f"Could not generate a new flight: {e}"}), 500

        results = []
        for flight in flights_list:
            current_price = calculate_dynamic_price(flight)
            results.append({
                "id": flight.id, "flight_number": flight.flight_number, "origin": flight.origin,
                "destination": flight.destination, "departure_time": flight.departure_time.isoformat(),
                "arrival_time": flight.arrival_time.isoformat(), "base_price": flight.base_price,
                "dynamic_price": current_price, "seats_available": flight.seats_available
            })
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 8. BOOKING API ENDPOINTS (NOW SECURED) ---

@app.route('/api/bookings/create', methods=['POST'])
@jwt_required() # <-- SECURED
def create_booking():
    """ API endpoint to create a new booking. Must be logged in. """
    data = request.get_json()
    
    # Get user ID from the login token
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not data or not data.get('flight_id') or not data.get('seat_number'):
        return jsonify({"error": "Missing flight_id or seat_number"}), 400

    try:
        flight = Flight.query.with_for_update().get(data['flight_id'])
        if not flight:
            return jsonify({"error": "Flight not found."}), 404
        if flight.seats_available <= 0:
            return jsonify({"error": "This flight is sold out."}), 400

        final_price = calculate_dynamic_price(flight)
        
        new_booking = Booking(
            flight_id=flight.id,
            user_id=current_user_id, # <-- Link to user
            # Use the user's name/email from their profile
            passenger_name=user.name,
            passenger_email=user.email,
            seat_number=data['seat_number'],
            pnr=generate_pnr(),
            price_paid=final_price,
            status='CONFIRMED'
        )

        flight.seats_available -= 1
        db.session.add(new_booking)
        db.session.commit()

        return jsonify({
            "message": "Booking successful!",
            "booking": {
                "pnr": new_booking.pnr, "flight_number": flight.flight_number,
                "passenger_name": new_booking.passenger_name, "status": new_booking.status,
                "booking_time": new_booking.booking_time.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Booking failed: {e}"}), 500

@app.route('/api/bookings/my-bookings', methods=['GET'])
@jwt_required() # <-- SECURED
def get_my_bookings():
    """ API endpoint to retrieve all bookings for the logged-in user. """
    current_user_id = get_jwt_identity()
    try:
        bookings = Booking.query.filter_by(user_id=current_user_id).order_by(Booking.booking_time.desc()).all()
        results = []
        for booking in bookings:
            results.append({
                "pnr": booking.pnr, "status": booking.status,
                "passenger_name": booking.passenger_name, "seat_number": booking.seat_number,
                "price_paid": booking.price_paid, "booking_time": booking.booking_time.isoformat(),
                "flight_number": booking.flight.flight_number, "origin": booking.flight.origin,
                "destination": booking.flight.destination, "departure_time": booking.flight.departure_time.isoformat()
            })
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bookings/<pnr>', methods=['GET'])
@jwt_required() # <-- SECURED
def get_booking_by_pnr(pnr):
    """ API endpoint to retrieve a specific booking by PNR.
        Ensures the booking belongs to the logged-in user. """
    current_user_id = get_jwt_identity()
    try:
        # User can only get their *own* booking
        booking = Booking.query.filter_by(pnr=pnr, user_id=current_user_id).first()
        if not booking:
            return jsonify({"error": "Booking not found or you do not have permission."}), 404
        
        return jsonify({
            "pnr": booking.pnr, "status": booking.status, "passenger_name": booking.passenger_name,
            "passenger_email": booking.passenger_email, "seat_number": booking.seat_number,
            "price_paid": booking.price_paid, "booking_time": booking.booking_time.isoformat(),
            "flight_number": booking.flight.flight_number, "origin": booking.flight.origin,
            "destination": booking.flight.destination, "departure_time": booking.flight.departure_time.isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bookings/<pnr>/cancel', methods=['POST'])
@jwt_required() # <-- SECURED
def cancel_booking(pnr):
    """ API endpoint to cancel a booking.
        Ensures the booking belongs to the logged-in user. """
    current_user_id = get_jwt_identity()
    try:
        # User can only cancel their *own* booking
        booking = Booking.query.with_for_update().filter_by(pnr=pnr, user_id=current_user_id).first()

        if not booking:
            return jsonify({"error": "Booking not found or you do not have permission."}), 404
        if booking.status == 'CANCELLED':
            return jsonify({"error": "This booking is already cancelled."}), 400

        flight = Flight.query.with_for_update().get(booking.flight_id)
        if not flight:
             return jsonify({"error": "Associated flight not found."}), 500

        booking.status = 'CANCELLED'
        flight.seats_available += 1
        db.session.commit()

        return jsonify({
            "message": "Booking successfully cancelled.",
            "booking": {
                "pnr": booking.pnr, "status": booking.status,
                "flight_number": flight.flight_number, "passenger_name": booking.passenger_name
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Cancellation failed: {e}"}), 500


# --- 9. Main Execution ---
if __name__ == '__main__':
    # This 'with' block creates the database tables
    # if they don't exist. It won't delete existing data.
    with app.app_context():
        db.create_all()
    
    # This starts the web server
    app.run(debug=True)

