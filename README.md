# ✈️ Ur Flight Mate: Flight Booking Simulator with Dynamic Pricing

This project is a full-stack web application designed to simulate a modern flight booking system. It features secure user authentication (sign-up/login), protected booking transactions, and a real-time **dynamic pricing engine** driven by seat availability and time until departure.

The architecture uses a Flask API backend for business logic and data persistence, paired with a lightweight React/Vite frontend for the user interface.

## ✨ Core Features

* **Dynamic Pricing:** Flight prices are calculated instantly upon search, increasing as **seats fill up** and as the **departure date approaches** (e.g., prices surge days before a flight).
* **Secure Authentication:** Users can register and log in via a REST API secured with **JWT (JSON Web Tokens)**.
* **Protected Booking:** All booking creation and management endpoints require a valid JWT, ensuring transactions are linked to the logged-in user.
* **Concurrency Safe Transactions:** The backend is designed to handle bookings and cancellations atomically, preventing race conditions that could lead to double-booking seats.
* **Demand Simulation:** A separate Python script (`demand_simulator.py`) runs in the background to randomly "book" seats, simulating real-world demand and visibly changing flight prices for users.
* **Booking Management:** Users can view a list of all their booked flights and **cancel** existing confirmed bookings, which automatically returns the seat to the flight inventory.
* **On-Demand Flight Generation:** If a user searches for a route with no existing flights, the system auto-generates a new flight to ensure results are always available.

## 🏛️ Technology Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend API** | Python, **Flask** | RESTful API endpoints for Auth, Search, Booking, and Management. |
| **Authentication** | **Flask-JWT-Extended**, **Flask-Bcrypt** | JWT token management and secure password hashing. |
| **Database** | **Flask-SQLAlchemy**, **SQLite** | Simple, file-based persistence for `User`, `Flight`, and `Booking` data. |
| **Frontend UI** | JavaScript, HTML, **Tailwind CSS** | Single-page application (SPA) user interface. |
| **Development Tooling** | **Vite**, React, ESLint | Modern bundling, local development server, and code quality checks. |

## ⚙️ Setup and Running the Project

### Prerequisites

1.  Python (3.7+)
2.  Node.js (18+) & npm

### Step 1: Backend Setup and Execution

1.  **Navigate to the backend directory** (assuming your Python files are at the root or within a `backend/` folder).
2.  **Create a virtual environment** and activate it:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use: .\venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install Flask Flask-SQLAlchemy Flask-CORS Flask-Bcrypt Flask-JWT-Extended
    ```
4.  **Initialize and Seed the Database:**
    * This step creates the `flights.db` file and populates it with initial flight data.
    ```bash
    python seed.py
    ```
5.  **Start the Flask API Server:**
    ```bash
    python app.py
    # Server will run on [http://127.0.0.1:5000](http://127.0.0.1:5000)
    ```
6.  **(Optional) Start the Demand Simulator:**
    * Run this in a **separate terminal window** to see dynamic pricing in action as seats are sold over time.
    ```bash
    python demand_simulator.py
    ```

### Step 2: Frontend Setup and Execution

The frontend uses Vite and is a pure HTML/JS file (`index.html`) running within the Vite development environment for live reloading and asset serving.

1.  **Navigate to the frontend directory** (assuming `package.json` is at the root or within a `frontend/` folder).
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Start the Development Server:**
    ```bash
    npm run dev
    # Server will run on http://localhost:5173 (or similar)
    ```

## 🚀 Usage

1.  Open the frontend URL (e.g., `http://localhost:5173`) in your browser.
2.  **Sign Up** for a new account (or log in if you already created one).
3.  Navigate to the **Search** view, select your origin, destination (e.g., 'New York (JFK)' to 'Los Angeles (LAX)'), and a future date.
4.  Click **Search Flights** to see dynamically calculated prices.
5.  Click **"Book Now"** on a flight, select a seat, and click **"Confirm & Pay"**.
6.  View your confirmed booking on the **"Your Flights"** page and test the **"Cancel Booking"** feature.