from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the database extension
db = SQLAlchemy()

# --- NEW: User Model ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # This creates a relationship, so we can do 'user.bookings'
    # to get all bookings for this user
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

# --- Flight Model (Unchanged) ---
class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(20), unique=True, nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    total_seats = db.Column(db.Integer, nullable=False)
    seats_available = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Flight {self.flight_number}>'
    
    # This relationship (backref) is created by the Booking model
    # We don't need to add 'bookings' here.

# --- Booking Model (UPDATED) ---
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # This 'Foreign Key' links the booking to a specific flight
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    
    # --- NEW: Link to the User ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Passenger info (we can get this from the user object now,
    # but we'll keep it for simplicity)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_email = db.Column(db.String(100), nullable=False)
    
    # A unique booking reference, like "AB12CD"
    pnr = db.Column(db.String(10), unique=True, nullable=False)
    
    seat_number = db.Column(db.String(5), nullable=False) # e.g., "12A"
    price_paid = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='CONFIRMED') # e.g., CONFIRMED, CANCELLED
    booking_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # This relationship lets us do 'booking.flight'
    flight = db.relationship('Flight', backref=db.backref('bookings', lazy=True))
    
    # The 'booking.user' relationship is created by the backref in the User model

    def __repr__(self):
        return f'<Booking {self.pnr}>'

