from datetime import datetime

def calculate_dynamic_price(flight):
    """
    Calculates a dynamic price for a flight based on rules.
    Input: A 'Flight' object
    Output: The new calculated price (float)
    """
    
    # --- Factor 1: Seat Occupancy ---
    # Calculate how full the flight is (as a percentage, 0.0 to 1.0)
    try:
        occupancy_pct = 1.0 - (flight.seats_available / flight.total_seats)
    except ZeroDivisionError:
        # This handles a weird case where total_seats is 0
        occupancy_pct = 1.0 

    # We use (occupancy_pct ** 2) to make the price
    # increase *faster* as the flight gets fuller.
    # A half-full flight (0.5) = 1 + (0.25 * 1.5) = 1.375x price
    # A 90% full flight (0.9) = 1 + (0.81 * 1.5) = 2.215x price
    seat_multiplier = 1.0 + (occupancy_pct ** 2) * 1.5

    # --- Factor 2: Time Until Departure ---
    # Get the current time and compare it to the flight's departure
    now = datetime.now()
    days_until_departure = (flight.departure_time - now).days

    time_multiplier = 1.0 # Default multiplier

    if days_until_departure < 2:
        # Less than 2 days away? Big price jump!
        time_multiplier = 2.0
    elif days_until_departure < 7:
        # Less than 1 week away? Medium price jump.
        time_multiplier = 1.5
    elif days_until_departure < 30:
        # Less than 1 month away? Small price jump.
        time_multiplier = 1.2
    
    # --- Final Calculation ---
    # New price = Base * (Seat Logic) * (Time Logic)
    
    dynamic_price = flight.base_price * seat_multiplier * time_multiplier
    
    # Return the price, rounded to 2 decimal places
    return round(dynamic_price, 2)
