import time
import random
from app import app, db, Flight

def simulate_demand():
    """
    A background script that will randomly 'book' seats to
    simulate real-world demand.
    """
    print("--- Demand Simulator Started ---")
    print("Press Ctrl+C to stop the simulator.")
    
    while True:
        try:
            # We need to run this 'with' block
            # to make sure our script can talk to the app and database
            with app.app_context():
                
                # 1. Find a random flight that still has seats
                available_flights = Flight.query.filter(Flight.seats_available > 0).all()
                
                if not available_flights:
                    print("All flights are fully booked!")
                    break
                    
                # 2. Pick one of those flights at random
                flight_to_book = random.choice(available_flights)
                
                # 3. 'Book' a random number of seats (1 to 3)
                seats_to_book = random.randint(1, 3)
                
                # Make sure we don't book more seats than are left
                if seats_to_book > flight_to_book.seats_available:
                    seats_to_book = flight_to_book.seats_available
                    
                # 4. Update the database
                flight_to_book.seats_available -= seats_to_book
                db.session.commit()
                
                print(f"Booked {seats_to_book} seat(s) on Flight {flight_to_book.flight_number}.")
                print(f"  > Flight {flight_to_book.flight_number} now has {flight_to_book.seats_available} seats left.")

            # 5. Wait for a random time (e.g., 2 to 5 seconds) before booking again
            time.sleep(random.randint(2, 5))
            
        except KeyboardInterrupt:
            # This allows us to stop the script with Ctrl+C
            print("\n--- Demand Simulator Stopped ---")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)

if __name__ == '__main__':
    simulate_demand()