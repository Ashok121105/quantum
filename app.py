import streamlit as st
import pandas as pd
import numpy as np
import folium
import math
import sqlite3
import random
from datetime import datetime, timedelta
from streamlit_folium import st_folium

# ============================================================
# QUANTUM-INSPIRED GREEN FLEET OPTIMIZER
# Prediction + Optimization + Voyage Monitoring + Safety Alerts
# ============================================================

st.set_page_config(
    page_title="Green Fleet AI",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "fleet_database.db"

# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            origin TEXT,
            destination TEXT,
            distance_km REAL,
            ship_capacity REAL,
            speed_knots REAL,
            fuel_type TEXT,
            weather TEXT,
            predicted_fuel REAL,
            optimized_fuel REAL,
            current_cost REAL,
            optimized_cost REAL,
            current_co2 REAL,
            optimized_co2 REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS voyage_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            voyage TEXT,
            segment REAL,
            temperature REAL,
            vibration REAL,
            pressure REAL,
            leakage REAL,
            health TEXT,
            alert TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_prediction(data):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions
        (timestamp, origin, destination, distance_km, ship_capacity,
         speed_knots, fuel_type, weather, predicted_fuel, optimized_fuel,
         current_cost, optimized_cost, current_co2, optimized_co2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()


def clear_history():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM predictions")
    cur.execute("DELETE FROM voyage_segments")
    conn.commit()
    conn.close()


def get_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM predictions ORDER BY id DESC", conn
    )
    conn.close()
    return df


init_db()

# ------------------------------------------------------------
# WORLD DESTINATIONS
# Coordinates are representative city/port coordinates.
# ------------------------------------------------------------
PORTS = {
    "Chennai, India": (13.0827, 80.2707),
    "Mumbai, India": (19.0760, 72.8777),
    "Visakhapatnam, India": (17.6868, 83.2185),
    "Kochi, India": (9.9312, 76.2673),
    "Goa, India": (15.4909, 73.8278),
    "Kolkata, India": (22.5726, 88.3639),
    "Singapore": (1.3521, 103.8198),
    "Dubai, UAE": (25.2048, 55.2708),
    "Abu Dhabi, UAE": (24.4539, 54.3773),
    "Colombo, Sri Lanka": (6.9271, 79.8612),
    "Port Klang, Malaysia": (3.0000, 101.4000),
    "Jakarta, Indonesia": (-6.2088, 106.8456),
    "Shanghai, China": (31.2304, 121.4737),
    "Hong Kong": (22.3193, 114.1694),
    "Tokyo, Japan": (35.6762, 139.6503),
    "Busan, South Korea": (35.1796, 129.0756),
    "Manila, Philippines": (14.5995, 120.9842),
    "Sydney, Australia": (-33.8688, 151.2093),
    "Melbourne, Australia": (-37.8136, 144.9631),
    "Perth, Australia": (-31.9505, 115.8605),
    "Auckland, New Zealand": (-36.8509, 174.7645),
    "Cape Town, South Africa": (-33.9249, 18.4241),
    "Durban, South Africa": (-29.8587, 31.0218),
    "Mombasa, Kenya": (-4.0435, 39.6682),
    "Port Said, Egypt": (31.2653, 32.3019),
    "Istanbul, Turkey": (41.0082, 28.9784),
    "Athens, Greece": (37.9838, 23.7275),
    "Rotterdam, Netherlands": (51.9244, 4.4777),
    "Hamburg, Germany": (53.5511, 9.9937),
    "London, UK": (51.5074, -0.1278),
    "Lisbon, Portugal": (38.7223, -9.1393),
    "New York, USA": (40.7128, -74.0060),
    "Miami, USA": (25.7617, -80.1918),
    "Houston, USA": (29.7604, -95.3698),
    "Los Angeles, USA": (34.0522, -118.2437),
    "Vancouver, Canada": (49.2827, -123.1207),
    "Panama City, Panama": (8.9824, -79.5199),
    "Rio de Janeiro, Brazil": (-22.9068, -43.1729),
    "Buenos Aires, Argentina": (-34.6037, -58.3816),
    "Valparaiso, Chile": (-33.0472, -71.6127),
}

FUEL_DATA = {
    "Diesel": {
        "consumption_factor": 1.00,
        "co2_factor": 3.20,
        "price": 65000,
        "green_score": 35,
    },
    "Petrol": {
        "consumption_factor": 1.08,
        "co2_factor": 3.10,
        "price": 70000,
        "green_score": 30,
    },
    "LNG": {
        "consumption_factor": 0.94,
        "co2_factor": 2.75,
        "price": 57000,
        "green_score": 62,
    },
    "Methanol": {
        "consumption_factor": 1.02,
        "co2_factor": 1.95,
        "price": 61000,
        "green_score": 75,
    },
    "Hydrogen": {
        "consumption_factor": 0.72,
        "co2_factor": 0.55,
        "price": 92000,
        "green_score": 91,
    },
    "Ammonia": {
        "consumption_factor": 0.86,
        "co2_factor": 0.30,
        "price": 72000,
        "green_score": 88,
    },
}

WEATHER_FACTOR = {
    "Calm Sea": 0.92,
    "Normal": 1.00,
    "Moderate": 1.08,
    "Heavy": 1.18,
    "Storm": 1.32,
}

# ------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def route_distance(origin, destination):
    a = PORTS[origin]
    b = PORTS[destination]
    # Sea routes are longer than great-circle distance.
    return haversine_km(a[0], a[1], b[0], b[1]) * 1.12


def estimate_base_fuel(distance_km, capacity_tonnes, speed_knots,
                       fuel_type, weather):
    """
    Educational simulation model.
    It is NOT a certified marine-engine fuel model.
    """
    capacity_factor = 1.0 + max(0, capacity_tonnes - 10000) / 100000
    speed_factor = (max(speed_knots, 1) / 12.0) ** 2.3
    fuel_factor = FUEL_DATA[fuel_type]["consumption_factor"]
    weather_factor = WEATHER_FACTOR[weather]

    # Approximate baseline litres/km.
    litres_per_km = 0.42 * capacity_factor * speed_factor
    fuel = distance_km * litres_per_km * fuel_factor * weather_factor

    return max(fuel, 1.0)


def calculate_cost(fuel_litres, fuel_type):
    # Fuel price field is treated as price per 1000 litres for demo.
    return fuel_litres * (FUEL_DATA[fuel_type]["price"] / 1000.0)


def calculate_co2(fuel_litres, fuel_type):
    return fuel_litres * FUEL_DATA[fuel_type]["co2_factor"]


def quantum_inspired_optimize(distance, capacity, current_speed,
                              fuel_type, weather):
    """
    Quantum-inspired classical search.

    We create a set of candidate operating states, score them,
    and select the lowest objective. This is a classical
    optimization simulation inspired by search over multiple
    possible states; it does not require a quantum computer.
    """
    candidates = []

    speed_min = max(8.0, current_speed - 4.0)
    speed_max = min(25.0, current_speed + 2.0)

    for speed in np.linspace(speed_min, speed_max, 25):
        fuel = estimate_base_fuel(
            distance, capacity, speed, fuel_type, weather
        )
        cost = calculate_cost(fuel, fuel_type)
        co2 = calculate_co2(fuel, fuel_type)

        # Lower is better.
        speed_penalty = abs(speed - current_speed) * 1000
        objective = (
            cost * 0.55
            + co2 * 12000 * 0.35
            + speed_penalty
        )

        candidates.append({
            "speed": speed,
            "fuel": fuel,
            "cost": cost,
            "co2": co2,
            "objective": objective
        })

    best = min(candidates, key=lambda x: x["objective"])
    return best, pd.DataFrame(candidates)


def health_status(temp, vibration, pressure, leakage):
    """
    Demo safety thresholds. Real ships must use OEM/class-approved
    limits for their actual engine and fuel system.
    """
    alerts = []

    if temp >= 120:
        alerts.append("CRITICAL: Engine temperature extremely high")
    elif temp >= 105:
        alerts.append("WARNING: High engine temperature")

    if vibration >= 8:
        alerts.append("CRITICAL: Abnormal vibration")
    elif vibration >= 5:
        alerts.append("WARNING: Elevated vibration")

    if pressure < 2.0 or pressure > 8.0:
        alerts.append("CRITICAL: Fuel-system pressure outside safe demo range")
    elif pressure < 2.5 or pressure > 7.5:
        alerts.append("WARNING: Fuel-system pressure abnormal")

    if leakage >= 5:
        alerts.append("CRITICAL: Possible fuel leak detected")
    elif leakage >= 1:
        alerts.append("WARNING: Possible fuel leakage")

    if any(x.startswith("CRITICAL") for x in alerts):
        return "CRITICAL", alerts
    if alerts:
        return "WARNING", alerts
    return "SAFE", ["All monitored values are within demo thresholds"]


def generate_sensor_values(fuel_type, seed=None):
    rng = random.Random(seed)

    temp = rng.uniform(75, 92)
    vibration = rng.uniform(1.2, 3.5)
    pressure = rng.uniform(3.5, 6.0)
    leakage = 0.0

    # Fuel-specific simulation variation.
    if fuel_type == "Ammonia":
        temp += rng.uniform(0, 4)
        pressure += rng.uniform(0, 0.5)
    elif fuel_type == "Hydrogen":
        pressure += rng.uniform(0, 0.7)

    return temp, vibration, pressure, leakage


def create_route_points(start, end, n=25):
    lat1, lon1 = PORTS[start]
    lat2, lon2 = PORTS[end]

    points = []
    for i in range(n):
        t = i / (n - 1)
        lat = lat1 + (lat2 - lat1) * t
        lon = lon1 + (lon2 - lon1) * t

        # Small curved deviation for visual route representation.
        curve = math.sin(t * math.pi) * 2.0
        lat += curve

        points.append((lat, lon))

    return points


# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.title("🚢 Green Fleet AI")
st.caption(
    "Fuel Prediction • Quantum-Inspired Optimization • Voyage Monitoring • Safety Alerts"
)

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Voyage Setup")

    origin = st.selectbox(
        "Starting Port",
        list(PORTS.keys()),
        index=list(PORTS.keys()).index("Chennai, India")
    )

    destination_options = [x for x in PORTS.keys() if x != origin]
    default_dest = (
        destination_options.index("Mumbai, India")
        if "Mumbai, India" in destination_options else 0
    )

    destination = st.selectbox(
        "Destination",
        destination_options,
        index=default_dest
    )

    ship_capacity = st.number_input(
        "Ship Capacity (tonnes)",
        min_value=100.0,
        max_value=500000.0,
        value=10000.0,
        step=500.0
    )

    speed = st.slider(
        "Cruising Speed (knots)",
        min_value=6.0,
        max_value=25.0,
        value=14.0,
        step=0.5
    )

    fuel_type = st.selectbox(
        "Fuel Type",
        list(FUEL_DATA.keys()),
        index=0
    )

    weather = st.selectbox(
        "Sea / Weather Condition",
        list(WEATHER_FACTOR.keys()),
        index=1
    )

    st.divider()
    st.subheader("📡 Monitoring Mode")

    monitoring_mode = st.radio(
        "Sensor data",
        ["Simulation", "Manual sensor input"],
        index=0
    )

    st.info(
        "This prototype uses simulated/manual sensor values. "
        "For real deployment, connect approved ship sensors and use "
        "manufacturer/class-approved alarm limits."
    )

    run_button = st.button(
        "🚀 Analyze Voyage",
        type="primary",
        use_container_width=True
    )

    if st.button("🗑️ Clear History", use_container_width=True):
        clear_history()
        st.session_state.pop("analysis", None)
        st.session_state.pop("sensor_data", None)
        st.success("History cleared.")
        st.rerun()

# ------------------------------------------------------------
# MAIN CALCULATION
# ------------------------------------------------------------
distance = route_distance(origin, destination)

if run_button or "analysis" not in st.session_state:
    current_fuel = estimate_base_fuel(
        distance,
        ship_capacity,
        speed,
        fuel_type,
        weather
    )
    current_cost = calculate_cost(current_fuel, fuel_type)
    current_co2 = calculate_co2(current_fuel, fuel_type)

    optimized, candidates = quantum_inspired_optimize(
        distance,
        ship_capacity,
        speed,
        fuel_type,
        weather
    )

    analysis = {
        "origin": origin,
        "destination": destination,
        "distance": distance,
        "current_fuel": current_fuel,
        "current_cost": current_cost,
        "current_co2": current_co2,
        "optimized": optimized,
        "candidates": candidates,
        "timestamp": datetime.now()
    }

    st.session_state["analysis"] = analysis

    save_prediction((
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        origin,
        destination,
        distance,
        ship_capacity,
        speed,
        fuel_type,
        weather,
        current_fuel,
        optimized["fuel"],
        current_cost,
        optimized["cost"],
        current_co2,
        optimized["co2"]
    ))

analysis = st.session_state["analysis"]

# ------------------------------------------------------------
# TOP METRICS
# ------------------------------------------------------------
st.subheader("🧭 Voyage Overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance", f"{analysis['distance']:,.0f} km")
c2.metric("Current Fuel", f"{analysis['current_fuel']:,.0f} L")
c3.metric("Optimized Fuel", f"{analysis['optimized']['fuel']:,.0f} L")
c4.metric("Optimized Speed", f"{analysis['optimized']['speed']:.1f} kn")

# ------------------------------------------------------------
# PREDICTION + OPTIMIZATION
# ------------------------------------------------------------
st.subheader("🧠 Prediction & ⚛️ Optimization")

a, b = st.columns(2)

with a:
    st.markdown("### Current Operating Plan")
    st.write(f"**Fuel:** {fuel_type}")
    st.write(f"**Speed:** {speed:.1f} knots")
    st.write(f"**Weather:** {weather}")
    st.write(f"**Predicted fuel:** {analysis['current_fuel']:,.0f} L")
    st.write(f"**Estimated cost:** ₹{analysis['current_cost']:,.0f}")
    st.write(f"**Estimated CO₂:** {analysis['current_co2']:,.0f} kg")

with b:
    opt = analysis["optimized"]
    st.markdown("### Optimized Operating Plan")
    st.write(f"**Fuel:** {fuel_type}")
    st.write(f"**Recommended speed:** {opt['speed']:.1f} knots")
    st.write(f"**Predicted fuel:** {opt['fuel']:,.0f} L")
    st.write(f"**Estimated cost:** ₹{opt['cost']:,.0f}")
    st.write(f"**Estimated CO₂:** {opt['co2']:,.0f} kg")

fuel_saved = analysis["current_fuel"] - analysis["optimized"]["fuel"]
cost_saved = analysis["current_cost"] - analysis["optimized"]["cost"]
co2_saved = analysis["current_co2"] - analysis["optimized"]["co2"]

s1, s2, s3 = st.columns(3)
s1.metric(
    "⛽ Fuel Saving",
    f"{fuel_saved:,.0f} L",
    f"{(fuel_saved / analysis['current_fuel'] * 100):.1f}%"
)
s2.metric(
    "💰 Cost Saving",
    f"₹{cost_saved:,.0f}",
    f"{(cost_saved / analysis['current_cost'] * 100):.1f}%"
)
s3.metric(
    "🌱 CO₂ Reduction",
    f"{co2_saved:,.0f} kg",
    f"{(co2_saved / analysis['current_co2'] * 100):.1f}%"
)

# ------------------------------------------------------------
# MAP
# ------------------------------------------------------------
st.subheader("🌍 Voyage Map")

route = create_route_points(origin, destination)

mid_lat = (PORTS[origin][0] + PORTS[destination][0]) / 2
mid_lon = (PORTS[origin][1] + PORTS[destination][1]) / 2

m = folium.Map(
    location=[mid_lat, mid_lon],
    zoom_start=3,
    tiles="OpenStreetMap"
)

folium.Marker(
    PORTS[origin],
    tooltip=f"Start: {origin}",
    popup=f"🚢 Start Port<br>{origin}",
    icon=folium.Icon(icon="play", prefix="fa")
).add_to(m)

folium.Marker(
    PORTS[destination],
    tooltip=f"Destination: {destination}",
    popup=f"🎯 Destination<br>{destination}",
    icon=folium.Icon(icon="flag", prefix="fa")
).add_to(m)

folium.PolyLine(
    route,
    weight=4,
    opacity=0.8,
    tooltip=f"{origin} → {destination}"
).add_to(m)

# Ship marker starts near origin for the demo.
ship_point = route[min(1, len(route) - 1)]

folium.Marker(
    ship_point,
    tooltip="🚢 Ship",
    popup=(
        f"Ship<br>"
        f"Route: {origin} → {destination}<br>"
        f"Fuel: {fuel_type}"
    ),
    icon=folium.Icon(icon="ship", prefix="fa")
).add_to(m)

st_folium(
    m,
    width=None,
    height=500,
    returned_objects=[]
)

st.caption(
    "Map route is a visual approximation between selected ports. "
    "For real navigation, integrate an approved marine routing service."
)

# ------------------------------------------------------------
# VOYAGE DURATION
# ------------------------------------------------------------
hours = distance / (speed * 1.852)
days = hours / 24

st.subheader("⏱️ Estimated Voyage Duration")
d1, d2 = st.columns(2)
d1.metric("Estimated Hours", f"{hours:,.1f} h")
d2.metric("Estimated Days", f"{days:,.1f} days")

# ------------------------------------------------------------
# SAFETY MONITORING
# ------------------------------------------------------------
st.divider()
st.subheader("📡 Real-Time Ship Health Monitoring")

st.write(
    "This module demonstrates how a future onboard sensor/IoT system "
    "can send engine and fuel-system conditions to the control computer."
)

if monitoring_mode == "Simulation":
    seed = int(datetime.now().timestamp()) // 10
    temp, vibration, pressure, leakage = generate_sensor_values(
        fuel_type, seed
    )

    # Allow an optional demo fault injection.
    demo_fault = st.checkbox(
        "🧪 Demo: Inject an overheating/fault condition",
        value=False
    )

    if demo_fault:
        temp = 125.0
        vibration = 8.8
        pressure = 8.6
        leakage = 6.0

else:
    st.markdown("#### Enter Sensor Values")

    x1, x2 = st.columns(2)
    with x1:
        temp = st.number_input(
            "Engine Temperature (°C)",
            min_value=0.0,
            max_value=300.0,
            value=85.0,
            step=1.0
        )
        vibration = st.number_input(
            "Engine Vibration (mm/s)",
            min_value=0.0,
            max_value=30.0,
            value=2.5,
            step=0.1
        )

    with x2:
        pressure = st.number_input(
            "Fuel-System Pressure (bar)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.1
        )
        leakage = st.number_input(
            "Leak Sensor Reading (ppm / normalized demo value)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.1
        )

health, alerts = health_status(
    temp,
    vibration,
    pressure,
    leakage
)

h1, h2, h3, h4 = st.columns(4)
h1.metric("🌡️ Temperature", f"{temp:.1f} °C")
h2.metric("⚙️ Vibration", f"{vibration:.1f} mm/s")
h3.metric("⛽ Pressure", f"{pressure:.1f} bar")
h4.metric("🧪 Leakage", f"{leakage:.1f}")

if health == "SAFE":
    st.success("🟢 SHIP HEALTH: SAFE")
elif health == "WARNING":
    st.warning("🟡 SHIP HEALTH: WARNING")
else:
    st.error("🔴 SHIP HEALTH: CRITICAL")

st.markdown("### 🚨 Alert Center")

for alert in alerts:
    if alert.startswith("CRITICAL"):
        st.error("🚨 " + alert)
    elif alert.startswith("WARNING"):
        st.warning("⚠️ " + alert)
    else:
        st.success("✅ " + alert)

# ------------------------------------------------------------
# AUTOMATIC RECOMMENDATION
# ------------------------------------------------------------
st.markdown("### 🛠️ System Recommendation")

if health == "CRITICAL":
    st.error(
        "IMMEDIATE ATTENTION: The prototype has detected a critical "
        "condition. Reduce operational load if appropriate and follow "
        "the vessel's approved emergency/engineering procedures. "
        "Do not rely on this prototype as a safety-critical controller."
    )
elif health == "WARNING":
    st.warning(
        "INSPECTION ADVISED: Abnormal values were detected. "
        "Continue monitoring and inspect the relevant system according "
        "to approved vessel procedures."
    )
else:
    st.info(
        "Normal demo condition. Continue monitoring engine temperature, "
        "vibration, pressure and leakage."
    )

# ------------------------------------------------------------
# SENSOR HISTORY / CONTINUOUS SIMULATION
# ------------------------------------------------------------
st.markdown("### 📈 Continuous Monitoring Simulation")

if st.button("🔄 Generate 12 Monitoring Readings"):
    rows = []

    base_temp = temp
    base_vib = vibration
    base_pressure = pressure
    base_leak = leakage

    for i in range(12):
        t = datetime.now() + timedelta(minutes=i * 10)

        # Smooth simulated movement.
        tt = base_temp + math.sin(i / 2) * 2 + random.uniform(-1, 1)
        vv = max(0, base_vib + math.sin(i / 3) * 0.4 + random.uniform(-0.2, 0.2))
        pp = base_pressure + math.sin(i / 4) * 0.15 + random.uniform(-0.1, 0.1)
        ll = max(0, base_leak + random.uniform(-0.05, 0.05))

        hs, al = health_status(tt, vv, pp, ll)

        rows.append({
            "Time": t.strftime("%H:%M:%S"),
            "Temperature °C": round(tt, 2),
            "Vibration mm/s": round(vv, 2),
            "Pressure bar": round(pp, 2),
            "Leakage": round(ll, 2),
            "Health": hs,
            "Alert": " | ".join(al)
        })

        conn = sqlite3.connect(DB_FILE)
        conn.execute("""
            INSERT INTO voyage_segments
            (timestamp, voyage, segment, temperature, vibration,
             pressure, leakage, health, alert)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t.strftime("%Y-%m-%d %H:%M:%S"),
            f"{origin} → {destination}",
            i + 1,
            tt, vv, pp, ll, hs, " | ".join(al)
        ))
        conn.commit()
        conn.close()

    sensor_df = pd.DataFrame(rows)
    st.session_state["sensor_data"] = sensor_df

if "sensor_data" in st.session_state:
    sdf = st.session_state["sensor_data"]
    st.dataframe(sdf, use_container_width=True, hide_index=True)

    chart_df = sdf.set_index("Time")[
        ["Temperature °C", "Vibration mm/s", "Pressure bar"]
    ]
    st.line_chart(chart_df)

# ------------------------------------------------------------
# HISTORY
# ------------------------------------------------------------
st.divider()
st.subheader("🧾 Voyage History")

history = get_history()

if history.empty:
    st.info("No voyage history yet.")
else:
    display_cols = [
        "timestamp",
        "origin",
        "destination",
        "distance_km",
        "fuel_type",
        "predicted_fuel",
        "optimized_fuel",
        "current_cost",
        "optimized_cost",
        "current_co2",
        "optimized_co2",
    ]

    st.dataframe(
        history[display_cols],
        use_container_width=True,
        hide_index=True
    )

# ------------------------------------------------------------
# PROJECT EXPLANATION
# ------------------------------------------------------------
with st.expander("ℹ️ How this system works"):
    st.markdown("""
### 1. Fuel Prediction
The system estimates fuel consumption from distance, ship capacity,
speed, fuel type and weather.

### 2. Quantum-Inspired Optimization
A classical search evaluates many possible speed states and selects
the state with the lowest combined cost/CO₂ objective.

### 3. Green Decision Support
The system compares the current plan with the optimized plan and
reports fuel, cost and CO₂ savings.

### 4. Ship Health Monitoring
Temperature, vibration, pressure and leakage values can be monitored
continuously.

### 5. Alert System
If a monitored value crosses a configured demonstration threshold,
the dashboard displays SAFE, WARNING or CRITICAL status.

### 6. Real-World Integration
For a real vessel, the sensor layer can be connected through an
approved IoT/ship communication system. Safety thresholds must come
from the actual engine/fuel-system manufacturer, vessel procedures
and applicable maritime/class requirements.
""")

st.caption(
    "Prototype / educational decision-support software. "
    "It is not a certified navigation, engine-control, emergency, "
    "or safety system."
)
