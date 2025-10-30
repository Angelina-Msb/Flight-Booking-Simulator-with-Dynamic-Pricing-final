from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy outside of the app setup
db = SQLAlchemy()

# --- User Model ---
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Relationship to Booking records
    bookings = db.relationship('Booking', backref='owner', lazy=True)

# --- Flight Model ---
class Flight(db.Model):
    __tablename__ = 'flight'
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(20), nullable=False, unique=True)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    
    # Pricing/Inventory
    base_price = db.Column(db.Float, nullable=False) # Base price in USD
    total_seats = db.Column(db.Integer, nullable=False)
    seats_available = db.Column(db.Integer, nullable=False)

# --- Booking Model (Required for Booking Logic) ---
class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    
    # Core Booking Details
    pnr = db.Column(db.String(6), unique=True, nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_email = db.Column(db.String(120), nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    price_paid = db.Column(db.Float, nullable=False) # Raw INR value
    status = db.Column(db.String(20), default='CONFIRMED', nullable=False)
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Flight details
    flight = db.relationship('Flight', backref=db.backref('bookings', lazy=True))