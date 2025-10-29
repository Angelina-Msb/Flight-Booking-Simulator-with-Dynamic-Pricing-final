from app import app, db, Flight
from datetime import datetime, timedelta

# This function will create our sample data
def seed_data():
    print("Deleting old data...")
    # Clear out any old data
    Flight.query.delete()

    print("Creating new flight data...")
    
    # Create a list of sample flights
    flights = [
        Flight(
            flight_number="AA100",
            origin="New York (JFK)",
            destination="Los Angeles (LAX)",
            departure_time=datetime(2025, 11, 20, 9, 0, 0),
            arrival_time=datetime(2025, 11, 20, 12, 0, 0),
            base_price=350.00,
            total_seats=160,
            seats_available=160
        ),
        Flight(
            flight_number="UA200",
            origin="Chicago (ORD)",
            destination="Miami (MIA)",
            departure_time=datetime(2025, 11, 21, 14, 30, 0),
            arrival_time=datetime(2025, 11, 21, 18, 0, 0),
            base_price=220.00,
            total_seats=140,
            seats_available=140
        ),
        Flight(
            flight_number="DL300",
            origin="Los Angeles (LAX)",
            destination="New York (JFK)",
            departure_time=datetime(2025, 11, 20, 14, 0, 0),
            arrival_time=datetime(2025, 11, 20, 17, 0, 0),
            base_price=360.00,
            total_seats=160,
            seats_available=150 # Let's pretend 10 are booked
        ),
        Flight(
            flight_number="AA101",
            origin="New York (JFK)",
            destination="Los Angeles (LAX)",
            departure_time=datetime(2025, 11, 22, 11, 0, 0),
            arrival_time=datetime(2025, 11, 22, 14, 0, 0),
            base_price=340.00,
            total_seats=160,
            seats_available=160
        )
    ]

    # Add all the flights to the database session
    db.session.add_all(flights)
    
    # Commit the changes
    db.session.commit()
    print("Database has been seeded!")

# This 'if' block runs the function
if __name__ == '__main__':
    # We need to run this 'with' block
    # to make sure our script can talk to the app and database
    with app.app_context():
        seed_data()