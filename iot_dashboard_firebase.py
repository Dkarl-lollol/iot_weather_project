import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, db

# === FIREBASE SETUP ===
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_config.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://weathering-app-iot-default-rtdb.firebaseio.com/'
    })

# === Fetch data from Firebase ===
ref = db.reference("weather")
data = ref.get()

# === Convert to DataFrame ===
if data:
    df = pd.DataFrame(list(data.values()))
    df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
    df = df.sort_values("timestamp", ascending=False)
else:
    df = pd.DataFrame()

# === UI ===
st.title("🌤️ IoT Weather Dashboard (Firebase)")
st.write("Forecast vs Actual Comparison & MSE")

if df.empty:
    st.warning("⚠️ No data available in Firebase.")
else:
    # --- Data Table ---
    st.subheader("📋 Weather Data Table")
    st.dataframe(df)

    # --- Temperature Forecast vs Actual ---
    st.subheader("📈 Temperature: Forecast vs Actual")
    plt.figure(figsize=(10,4))
    plt.plot(df['timestamp'], df['temp_forecast'], label='Forecast', marker='o')
    plt.plot(df['timestamp'], df['temp_actual'], label='Actual', marker='x')
    plt.xticks(rotation=45)
    plt.ylabel("Temperature (°C)")
    plt.legend()
    st.pyplot(plt)

    # --- MSE Trend ---
    st.subheader("📉 Temperature MSE Trend")
    plt.figure(figsize=(10,4))
    plt.plot(df['timestamp'], df['temp_mse'], label='Temp MSE', color='red', marker='d')
    plt.xticks(rotation=45)
    plt.ylabel("MSE")
    st.pyplot(plt)
