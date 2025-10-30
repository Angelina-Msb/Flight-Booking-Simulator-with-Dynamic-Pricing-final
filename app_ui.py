import streamlit as st
import requests
from datetime import datetime, timedelta
import json, os

# ----------------------------------------------------
# --- CONFIGURATION ---
# ----------------------------------------------------
FLASK_API_URL = "http://127.0.0.1:5000"


# ----------------------------------------------------
# --- PERSISTENT TOKEN STORAGE (optional but recommended) ---
# ----------------------------------------------------
def save_token_to_file(token):
    with open(".jwtcache.json", "w") as f:
        json.dump({"token": token}, f)

def load_token_from_file():
    if os.path.exists(".jwtcache.json"):
        with open(".jwtcache.json", "r") as f:
            return json.load(f).get("token")
    return None


# ----------------------------------------------------
# --- SESSION INITIALIZATION ---
# ----------------------------------------------------
for key, default in {
    "logged_in": False,
    "token": None,
    "user_name": "",
    "user_id": None,
    "current_view": "auth",
    "auth_mode": "login",
    "search_results": [],
    "selected_flight": None,
    "last_booking_pnr": None,
}.items():
    st.session_state.setdefault(key, default)

# Load token from file if missing (persistence between reloads)
if not st.session_state.token:
    cached_token = load_token_from_file()
    if cached_token:
        st.session_state.token = cached_token
        st.session_state.logged_in = True
        st.session_state.current_view = "search"


# ----------------------------------------------------
# --- HELPER FUNCTIONS ---
# ----------------------------------------------------
def get_auth_headers():
    """Returns headers with the JWT token for protected API calls."""
    token = st.session_state.get("token")
    if token and isinstance(token, str) and token.strip():
        clean_token = token.strip().replace('"', '')
        return {"Authorization": f"Bearer {clean_token}"}
    return {}


# ----------------------------------------------------
# 1. AUTHENTICATION & SESSION MANAGEMENT
# ----------------------------------------------------
def show_auth_form():
    st.title("Welcome to Ur Flight Mate ✈️")
    st.header("Login / Sign-up")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Log In", use_container_width=True, key="login_btn"):
            st.session_state.auth_mode = 'login'
    with col2:
        if st.button("Sign Up", use_container_width=True, key="signup_btn"):
            st.session_state.auth_mode = 'signup'

    with st.form(key='auth_form'):
        email = st.text_input("Email/Username") 
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Submit")

        if submit_button:
            if st.session_state.auth_mode == 'login':
                response = requests.post(
                    f"{FLASK_API_URL}/api/auth/login", 
                    json={"email": email, "password": password}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    access_token = data.get('access_token')

                    # Store info in session
                    st.session_state.logged_in = True
                    st.session_state.token = access_token
                    st.session_state.user_name = data['user']['name']
                    st.session_state.user_id = data['user']['id']
                    st.session_state.current_view = 'search'

                    save_token_to_file(access_token)
                    
                    st.success(f"Welcome back, {data['user']['name']}!")
                    st.rerun()
                else:
                    st.error("Login failed. Check email and password.")

            elif st.session_state.auth_mode == 'signup':
                response = requests.post(
                    f"{FLASK_API_URL}/api/auth/signup", 
                    json={"name": email, "email": email, "password": password}
                )
                
                if response.status_code == 201:
                    st.success("Registration successful! Please log in.")
                    st.session_state.auth_mode = 'login'
                    st.rerun()
                elif response.status_code == 409:
                    st.error("User already exists. Please log in.")
                else:
                    st.error("Registration failed.")


# ----------------------------------------------------
# 2. FLIGHT SEARCH MODULE 
# ----------------------------------------------------
def show_flight_search():
    st.header("Find Your Flight 🌍")
    
    if st.session_state.last_booking_pnr:
        st.success(f"Last booking successful! PNR: {st.session_state.last_booking_pnr}")
        if st.button("Start New Search", key="new_search_btn"):
            st.session_state.last_booking_pnr = None
            st.session_state.search_results = []
            st.rerun()
    
    with st.form(key='search_form'):
        col1, col2, col3 = st.columns(3)
        with col1:
            origin = st.text_input("Origin City/Airport")
        with col2:
            destination = st.text_input("Destination City/Airport")
        with col3:
            min_date = datetime.now().date() + timedelta(days=1)
            travel_date = st.date_input("Travel Date", value=min_date, min_value=min_date)
        
        submit_search = st.form_submit_button("Search Flights")

    if submit_search and origin and destination:
        params = {
            "origin": origin,
            "destination": destination,
            "date": travel_date.strftime('%Y-%m-%d')
        }

        search_response = requests.get(
            f"{FLASK_API_URL}/api/flights/search", 
            params=params
        )

        if search_response.status_code == 200:
            st.session_state.search_results = search_response.json()
        else:
            st.error("No flights found for this route.")
            st.session_state.search_results = []

    if st.session_state.search_results:
        st.subheader(f"Results for {origin} to {destination}")

        for flight in st.session_state.search_results:
            col_flight, col_price, col_book = st.columns([3, 1.5, 1])
            dep_time = datetime.fromisoformat(flight['departure_time']).strftime('%I:%M %p')
            arr_time = datetime.fromisoformat(flight['arrival_time']).strftime('%I:%M %p')

            with col_flight:
                st.markdown(f"**{flight['flight_number']}** ({flight['origin']} → {flight['destination']})")
                st.markdown(f"Departure: {dep_time} | Arrival: {arr_time}")
            
            with col_price:
                st.success(f"**{flight['dynamic_price_formatted']}**")
                
            with col_book:
                if st.button("Book Now", key=f"book_{flight['id']}"):
                    st.session_state.selected_flight = flight
                    st.session_state.current_view = 'booking'
                    st.rerun()


# ----------------------------------------------------
# 3. BOOKING PAGE MODULE 
# ----------------------------------------------------
def show_booking_page():
    if not st.session_state.selected_flight:
        st.session_state.current_view = 'search'
        st.rerun()
        return

    flight = st.session_state.selected_flight
    
    if st.button("← Back to Search Results"):
        st.session_state.current_view = 'search'
        st.rerun()
        return

    surcharges = flight['price_breakdown']['surcharges']
    total_tax_component = surcharges.get('Taxes', 0) + surcharges.get('Dynamic Surcharge', 0)
    
    st.title("Complete Your Booking 🎟️")
    st.markdown(f"**{flight['flight_number']}** from {flight['origin']} to {flight['destination']}")
    st.subheader(f"Total Price: {flight['dynamic_price_formatted']}")
    st.markdown(f"Base Fare: {flight['base_price_inr_formatted']} | Taxes & Surcharges: **₹{total_tax_component:,.0f}**")
    
    st.markdown("---")
    
    with st.form(key='booking_form'):
        st.subheader("Passenger Details")
        seat_number = st.text_input("Desired Seat Number (e.g., 12A)", value="1A")
        st.success(f"Final Amount Due: **{flight['dynamic_price_formatted']}**")

        confirm_book = st.form_submit_button("Confirm & Pay")

        if confirm_book:
            auth_headers = get_auth_headers()

            # --- Debug Info ---
            st.write("DEBUG TOKEN:", st.session_state.token)
            st.write("DEBUG HEADERS:", auth_headers)

            if "Authorization" not in auth_headers:
                st.error("⚠️ Session expired. Please log in again.")
                return

            booking_payload = {
                "flight_id": flight['id'],
                "seat_number": seat_number,
            }

            booking_response = requests.post(
                f"{FLASK_API_URL}/api/bookings/create", 
                json=booking_payload, 
                headers=auth_headers
            )
            
            if booking_response.status_code == 201:
                booking_data = booking_response.json().get('booking', {})
                st.session_state.last_booking_pnr = booking_data.get('pnr')
                st.session_state.current_view = 'search'
                st.rerun()
            else:
                st.error(f"❌ Booking failed: {booking_response.json().get('error', 'Could not complete transaction.')}")



# ----------------------------------------------------
# 4. MAIN APPLICATION ENTRY POINT
# ----------------------------------------------------
def main_app():
    st.sidebar.title(f"Hello, {st.session_state.user_name} 👋")
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        # Reinitialize essential keys
        st.session_state.logged_in = False
        st.session_state.current_view = "auth"
        if os.path.exists(".jwtcache.json"):
            os.remove(".jwtcache.json")
        st.rerun()

    if st.session_state.current_view == 'search':
        show_flight_search()
    elif st.session_state.current_view == 'booking':
        show_booking_page()


# ----------------------------------------------------
# 5. RUN THE APPLICATION
# ----------------------------------------------------
if not st.session_state.logged_in:
    show_auth_form()
else:
    main_app()
