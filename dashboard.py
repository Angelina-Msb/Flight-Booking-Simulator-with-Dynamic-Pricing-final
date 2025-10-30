import streamlit as st
import pandas as pd
from app import app, db, Flight, calculate_dynamic_price
from datetime import datetime, timedelta
import random
import time # Ensure this is imported for any simulator loops, though we won't use it now.

# Define the flight ID you want to track (You MUST run 'python seed.py' first)
FLIGHT_ID_TO_TRACK = 1 

# --- CITY LIST (Copied from index.html) ---
CITIES = [
    "New York (JFK)", "Los Angeles (LAX)", "Chicago (ORD)", "Miami (MIA)",
    "San Francisco (SFO)", "Boston (BOS)", "London (LHR)", "Tokyo (NRT)",
    "Paris (CDG)", "Dubai (DXB)", "Mumbai (BOM)", "Delhi (DEL)",
    "Bangalore (BLR)", "Kolkata (CCU)"
]
CITIES.sort()

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(
    page_title="Ur Flight Mate Dashboard",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# -----------------------------------------------------------
# 1. SIDEBAR LAYOUT
# -----------------------------------------------------------
st.sidebar.title("✈️ Dynamic Search Filters")
st.sidebar.markdown("---")

origin_input = st.sidebar.selectbox("Origin", options=CITIES, index=CITIES.index("New York (JFK)") if "New York (JFK)" in CITIES else 0)
dest_input = st.sidebar.selectbox("Destination", options=CITIES, index=CITIES.index("Los Angeles (LAX)") if "Los Angeles (LAX)" in CITIES else 0)
date_input = st.sidebar.date_input("Departure Date", datetime.now().date())


# -----------------------------------------------------------
# 2. MAIN CONTENT LAYOUT
# -----------------------------------------------------------
st.title("📊 Flight Simulation Status")
st.markdown("---") 

# Define columns for the main content area (Metrics | Results)
metrics_col, data_col = st.columns([1, 3]) 


# --- 3. DATA FETCH AND DISPLAY FUNCTION ---
def update_dashboard():
    """
    Fetches the latest flight data, runs calculations, and updates the Streamlit elements.
    CRITICAL: This entire function runs within the Flask application context.
    """
    
    # CRITICAL FIX: Ensure the code runs inside the Flask app context
    with app.app_context():
        # Ensure tables exist (helpful during initial run)
        db.create_all()
        
        try:
            # 1. Fetch the flight data
            flight = Flight.query.get(FLIGHT_ID_TO_TRACK)
            
            if not flight:
                data_col.error(f"Flight ID {FLIGHT_ID_TO_TRACK} not found. Please run 'python seed.py' first.")
                return

            # --- CALCULATE DYNAMIC DATA (Using imported pricing logic) ---
            dynamic_price = calculate_dynamic_price(flight)
            occupancy_pct = round(1.0 - (flight.seats_available / flight.total_seats), 2)
            
            # CRITICAL FIX: Use accepted Streamlit keywords ('normal', 'inverse', 'off')
            seat_color_keyword = 'normal' # Default (Green/Good)
            if flight.seats_available < 50:
                seat_color_keyword = 'normal' 
            if flight.seats_available < 20:
                # Use 'inverse' to color the delta red/orange for low seats
                seat_color_keyword = 'inverse' 
            
            # 2. Update Metrics Column (Left Side of Main Content)
            with metrics_col:
                st.subheader("Price Metrics")
                
                # Dynamic Price Metric Card
                st.metric(
                    label=f"Current Fare ({flight.flight_number})",
                    value=f"${dynamic_price:.2f}",
                    delta=f"Base: ${flight.base_price:.2f}",
                    delta_color="off" # Use 'off' for a clean look on the base/dynamic price delta
                )
                
                # Seat Availability Metric Card
                st.metric(
                    label="Seats Available",
                    value=f"{flight.seats_available}",
                    delta=f"Occupancy: {occupancy_pct*100:.0f}%",
                    delta_color=seat_color_keyword # Applies the red/orange/green color
                )

            # 3. Update Results Column (Right Side of Main Content)
            with data_col:
                st.subheader("Simulated Flight Results")
                
                # Create a DataFrame for a neat table visualization
                flight_data = {
                    "Flight Number": [flight.flight_number],
                    "Route": [f"{flight.origin} -> {flight.destination}"],
                    "Departure Time": [flight.departure_time.strftime("%Y-%m-%d %H:%M")],
                    "Current Price": [f"${dynamic_price:.2f}"],
                    "Seats Remaining": [flight.seats_available],
                }
                df = pd.DataFrame(flight_data)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            # Display any deeper server/database error
            data_col.error(f"Database/Query Error: {e}")
            
# -----------------------------------------------------------
# 4. EXECUTION AND REFRESH
# -----------------------------------------------------------
update_dashboard()

# Add the Manual Refresh button and info at the bottom
if st.button("Manual Refresh (Click to see new dynamic price/seats!)"):
    st.rerun()

st.info("Remember to run 'python app.py' and 'python demand_simulator.py' in separate terminals to see the prices change.")