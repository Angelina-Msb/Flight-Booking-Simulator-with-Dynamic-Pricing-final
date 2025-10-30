from datetime import datetime
import math # Import math for rounding/ceilings

# Define conversion rate for simulator simplicity (e.g., 1 USD to 83 INR)
INR_RATE = 83.0

def calculate_dynamic_price(flight):
    """
    Calculates dynamic price and returns a dictionary of the price breakdown 
    in Indian Rupees (INR).
    """
    
    # --- 0. Initial Setup & Currency Conversion ---
    base_price_usd = flight.base_price
    # Convert base price to INR and round up to the nearest integer
    base_price_inr = math.ceil(base_price_usd * INR_RATE)
    
    # Initialize surcharges (in INR)
    surcharges = {
        'date_proximity_surcharge': 0,
        'occupancy_surcharge': 0,
        'class_premium': 0, # Placeholder for future class-based pricing
    }
    
    # --- Factor 1: Seat Occupancy ---
    try:
        occupancy_pct = 1.0 - (flight.seats_available / flight.total_seats)
    except ZeroDivisionError:
        occupancy_pct = 1.0 
        
    # Occupancy Surcharge Calculation: Base Price * (Occupancy^2) * 0.8
    # This makes the surcharge higher than the other one to reflect scarcity
    occupancy_multiplier = (occupancy_pct ** 2) * 0.8
    surcharges['occupancy_surcharge'] = math.ceil(base_price_inr * occupancy_multiplier)


    # --- Factor 2: Time Until Departure (Time Proximity) ---
    now = datetime.now()
    time_difference = flight.departure_time - now
    days_until_departure = time_difference.days

    if days_until_departure < 2:
        # Less than 2 days away? 35% surcharge.
        time_multiplier = 0.35
    elif days_until_departure < 7:
        # Less than 1 week away? 15% surcharge.
        time_multiplier = 0.15
    elif days_until_departure < 30:
        # Less than 1 month away? 5% surcharge.
        time_multiplier = 0.05
    else:
        time_multiplier = 0.0 # No surcharge for long lead times
        
    surcharges['date_proximity_surcharge'] = math.ceil(base_price_inr * time_multiplier)


    # --- Factor 3: Class Premium (Simple Placeholder) ---
    # Since we aren't tracking classes yet, we'll simulate a 10% premium 
    # to demonstrate the breakdown element.
    surcharges['class_premium'] = math.ceil(base_price_inr * 0.10)
    
    # --- Final Calculation ---
    total_surcharge = sum(surcharges.values())
    final_dynamic_price = base_price_inr + total_surcharge
    
    return {
        'final_price_inr': final_dynamic_price,
        'base_price_inr': base_price_inr,
        'surcharges': surcharges
    }