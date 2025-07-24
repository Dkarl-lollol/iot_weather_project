import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, db
import json
import os

# === STREAMLIT CLOUD FIREBASE SETUP ===
@st.cache_resource
def init_firebase():
    """Initialize Firebase with Streamlit secrets or local config"""
    try:
        if not firebase_admin._apps:
            # Try Streamlit Cloud secrets first
            if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                # Use Streamlit secrets (production/cloud)
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
                st.success("🔒 Using Streamlit Cloud secrets")
                
            # Fallback to local file for development
            elif os.path.exists("firebase_config.json"):
                with open("firebase_config.json", 'r') as f:
                    firebase_config = json.load(f)
                database_url = "https://weathering-app-iot-default-rtdb.firebaseio.com/"
                st.warning("⚠️ Using local firebase_config.json (development mode)")
                
            else:
                st.error("❌ No Firebase configuration found!")
                st.markdown("""
                **For Streamlit Cloud deployment:**
                - Make sure you added Firebase secrets in Advanced Settings
                
                **For local development:**
                - Create firebase_config.json file in your project directory
                """)
                return False

            # Initialize Firebase
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
            return True
            
    except Exception as e:
        st.error(f"❌ Firebase initialization failed: {e}")
        return False

# === FETCH DATA FROM FIREBASE ===
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_firebase_data():
    """Fetch weather data from Firebase"""
    try:
        ref = db.reference("weather")
        data = ref.get()
        return data
    except Exception as e:
        st.error(f"❌ Error fetching data from Firebase: {e}")
        return None

# === PROCESS DATA ===
def process_data(data):
    """Convert Firebase data to DataFrame"""
    if not data:
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(list(data.values()))
        
        # Rename columns
        df.rename(columns={
            'temp_actual': 'Actual Temp (°C)',
            'temp_forecast': 'Forecast Temp (°C)',
            'temp_mse': 'Temp MSE',
            'wind_actual': 'Actual Wind (km/h)',
            'wind_forecast': 'Forecast Wind (km/h)',
            'wind_mse': 'Wind MSE'
        }, inplace=True)
        
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
        df = df.sort_values("timestamp", ascending=False)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error processing data: {e}")
        return pd.DataFrame()

# === MAIN APP ===
def main():
    # Page configuration
    st.set_page_config(
        page_title="IoT Weather Dashboard",
        page_icon="🌤️",
        layout="wide"
    )
    
    # Title and description
    st.title("🌤️ IoT Weather Dashboard (Firebase)")
    st.write("Forecast vs Actual Comparison & MSE")
    
    # Show deployment status
    if hasattr(st, 'secrets') and 'firebase' in st.secrets:
        st.info("🚀 **Running on Streamlit Cloud** with secure secrets")
    else:
        st.info("💻 **Running locally** with firebase_config.json")
    
    # Initialize Firebase
    with st.spinner("Connecting to Firebase..."):
        firebase_initialized = init_firebase()
    
    if not firebase_initialized:
        st.stop()
    
    # Fetch data from Firebase
    with st.spinner("Loading weather data..."):
        data = fetch_firebase_data()
    
    # Process data
    df = process_data(data)
    
    # Check if data is available
    if df.empty:
        st.warning("⚠️ No data available in Firebase.")
        st.markdown("""
        **Possible reasons:**
        1. Backend service is not running
        2. No weather data has been collected yet
        3. Database connection issues
        
        **What to do:**
        - Check if your Flask backend is running
        - Wait for the next data collection cycle
        - Test Firebase connection below
        """)
        
        # Add connection test button
        if st.button("🧪 Test Firebase Connection"):
            try:
                ref = db.reference("weather")
                test_data = ref.limit_to_last(1).get()
                if test_data:
                    st.success("✅ Firebase connection successful!")
                    st.json(test_data)
                else:
                    st.warning("⚠️ Connected to Firebase but no data found")
            except Exception as e:
                st.error(f"❌ Connection test failed: {e}")
        return
    
    # Show data count
    st.success(f"✅ Successfully loaded {len(df)} weather data points")
    
    # === METRICS OVERVIEW ===
    st.subheader("📊 Latest Metrics")
    
    if not df.empty:
        latest_data = df.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            temp_diff = latest_data['Actual Temp (°C)'] - latest_data['Forecast Temp (°C)']
            st.metric(
                "Temperature (°C)", 
                f"{latest_data['Actual Temp (°C)']:.1f}",
                f"{temp_diff:+.1f}"
            )
        
        with col2:
            wind_diff = latest_data['Actual Wind (km/h)'] - latest_data['Forecast Wind (km/h)']
            st.metric(
                "Wind Speed (km/h)", 
                f"{latest_data['Actual Wind (km/h)']:.1f}",
                f"{wind_diff:+.1f}"
            )
        
        with col3:
            if 'Temp MSE' in df.columns:
                st.metric("Latest Temp MSE", f"{latest_data['Temp MSE']:.3f}")
        
        with col4:
            if 'Wind MSE' in df.columns:
                st.metric("Latest Wind MSE", f"{latest_data['Wind MSE']:.3f}")
    
    # === DATA TABLE ===
    st.subheader("📋 Weather Data Table")
    
    # Show recent data with better formatting
    display_df = df.head(20).copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(display_df, use_container_width=True)
    
    # === TEMPERATURE CHARTS ===
    st.subheader("📈 Temperature: Forecast vs Actual")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['timestamp'], df['Forecast Temp (°C)'], label='Forecast', marker='o', linewidth=2)
    ax.plot(df['timestamp'], df['Actual Temp (°C)'], label='Actual', marker='x', linewidth=2)
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    
    # === TEMPERATURE MSE TREND ===
    if 'Temp MSE' in df.columns:
        st.subheader("📉 Temperature MSE Trend")
        
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df['timestamp'], df['Temp MSE'], label='Temp MSE', color='red', marker='d', linewidth=2)
        ax.set_xlabel("Time")
        ax.set_ylabel("MSE")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
    
    # === WIND CHARTS ===
    st.subheader("💨 Wind: Forecast vs Actual")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['timestamp'], df['Forecast Wind (km/h)'], label='Forecast', marker='o', linewidth=2)
    ax.plot(df['timestamp'], df['Actual Wind (km/h)'], label='Actual', marker='x', linewidth=2)
    ax.set_xlabel("Time")
    ax.set_ylabel("Wind Speed (km/h)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    
    # === WIND MSE TREND ===
    if 'Wind MSE' in df.columns:
        st.subheader("📉 Wind MSE Trend")
        
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df['timestamp'], df['Wind MSE'], label='Wind MSE', color='blue', marker='d', linewidth=2)
        ax.set_xlabel("Time")
        ax.set_ylabel("MSE")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
    
    # === STATISTICS SUMMARY ===
    with st.expander("📊 Statistical Summary"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Temperature Statistics:**")
            temp_cols = [col for col in ['Forecast Temp (°C)', 'Actual Temp (°C)', 'Temp MSE'] if col in df.columns]
            if temp_cols:
                temp_stats = df[temp_cols].describe().round(3)
                st.dataframe(temp_stats)
        
        with col2:
            st.write("**Wind Statistics:**")
            wind_cols = [col for col in ['Forecast Wind (km/h)', 'Actual Wind (km/h)', 'Wind MSE'] if col in df.columns]
            if wind_cols:
                wind_stats = df[wind_cols].describe().round(3)
                st.dataframe(wind_stats)
    
    # === REFRESH BUTTON ===
    st.subheader("🔄 Controls")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("🧪 Test Firebase", type="secondary"):
            try:
                ref = db.reference("weather")
                test_data = ref.limit_to_last(1).get()
                if test_data:
                    st.success("✅ Firebase connection successful!")
                else:
                    st.warning("⚠️ Connected but no data found")
            except Exception as e:
                st.error(f"❌ Connection test failed: {e}")

# === RUN APP ===
if __name__ == "__main__":
    main()