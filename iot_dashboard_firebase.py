import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, db
import json
import os

# === FIREBASE SETUP (Working Version) ===
@st.cache_resource
def init_firebase():
    """Initialize Firebase with Streamlit secrets or local config"""
    if not firebase_admin._apps:
        try:
            # Try Streamlit Cloud secrets first
            if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                firebase_config = {
                    "type": st.secrets["firebase"]["type"],
                    "project_id": st.secrets["firebase"]["project_id"],
                    "private_key_id": st.secrets["firebase"]["private_key_id"],
                    "private_key": st.secrets["firebase"]["private_key"],
                    "client_email": st.secrets["firebase"]["client_email"],
                    "client_id": st.secrets["firebase"]["client_id"],
                    "auth_uri": st.secrets["firebase"]["auth_uri"],
                    "token_uri": st.secrets["firebase"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
                    "universe_domain": st.secrets["firebase"]["universe_domain"]
                }
                database_url = st.secrets["database"]["url"]
            # Fallback to local file
            elif os.path.exists("firebase_config.json"):
                with open("firebase_config.json", 'r') as f:
                    firebase_config = json.load(f)
                database_url = "https://weathering-app-iot-default-rtdb.firebaseio.com/"
            else:
                return False

            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {'databaseURL': database_url})
            return True
        except:
            return False
    return True

# === FETCH DATA FROM FIREBASE (Working Version) ===
@st.cache_data(ttl=300)
def get_weather_data():
    """Fetch and process weather data from Firebase"""
    try:
        ref = db.reference("weather")
        data = ref.get()
        
        if data:
            df = pd.DataFrame(list(data.values()))
            df.rename(columns={
                'temp_actual': 'Actual Temp (°C)',
                'temp_forecast': 'Forecast Temp (°C)',
                'temp_mse': 'Temp MSE',
                'wind_actual': 'Actual Wind (km/h)',
                'wind_forecast': 'Forecast Wind (km/h)',
                'wind_mse': 'Wind MSE'
            }, inplace=True)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
            df = df.sort_values("timestamp", ascending=False)
            return df
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()

# Initialize Firebase
firebase_ready = init_firebase()

# Get data from Firebase
if firebase_ready:
    df = get_weather_data()
else:
    df = pd.DataFrame()

# === UI (Your Original Simple Design) ===
st.title("🌤️ IoT Weather Dashboard (FireBase)")
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
    plt.plot(df['timestamp'], df['Forecast Temp (°C)'], label='Forecast', marker='o')
    plt.plot(df['timestamp'], df['Actual Temp (°C)'], label='Actual', marker='x')
    plt.xticks(rotation=45)
    plt.ylabel("Temperature (°C)")
    plt.legend()
    st.pyplot(plt)
    
    # --- Temperature MSE Trend ---
    st.subheader("📉 Temperature MSE Trend")
    plt.figure(figsize=(10,4))
    plt.plot(df['timestamp'], df['Temp MSE'], label='Temp MSE', color='red', marker='d')
    plt.xticks(rotation=45)
    plt.ylabel("MSE")
    st.pyplot(plt)
    
    # --- Wind Forecast vs Actual ---
    st.subheader("💨 Wind: Forecast vs Actual")
    plt.figure(figsize=(10,4))
    plt.plot(df['timestamp'], df['Forecast Wind (km/h)'], label='Forecast', marker='o')
    plt.plot(df['timestamp'], df['Actual Wind (km/h)'], label='Actual', marker='x')
    plt.xticks(rotation=45)
    plt.ylabel("Wind Speed (km/h)")
    plt.legend()
    st.pyplot(plt)
    
    # --- Wind MSE Trend ---
    st.subheader("📉 Wind MSE Trend")
    plt.figure(figsize=(10,4))
    plt.plot(df['timestamp'], df['Wind MSE'], label='Wind MSE', color='blue', marker='d')
    plt.xticks(rotation=45)
    plt.ylabel("MSE")
    st.pyplot(plt)