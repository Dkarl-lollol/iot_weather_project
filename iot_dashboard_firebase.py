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
                
            # Fallback to local file for development
            elif os.path.exists("firebase_config.json"):
                with open("firebase_config.json", 'r') as f:
                    firebase_config = json.load(f)
                database_url = "https://weathering-app-iot-default-rtdb.firebaseio.com/"
                
            else:
                st.error("❌ No Firebase configuration found!")
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
def fetch_weather_data():
    """Fetch weather data from Firebase"""
    try:
        ref = db.reference("weather")
        data = ref.get()
        
        if data is None:
            return pd.DataFrame()
        
        if not isinstance(data, dict):
            st.error("❌ Unexpected data format from Firebase")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(list(data.values()))
        
        if df.empty:
            return df
        
        # Check required columns
        required_columns = ['timestamp', 'temp_actual', 'temp_forecast', 'wind_actual', 'wind_forecast']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"❌ Missing required columns: {missing_columns}")
            return pd.DataFrame()
        
        # Rename columns for display
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
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

# === CONNECTION TEST ===
def test_firebase_connection():
    """Test Firebase connection"""
    try:
        ref = db.reference("weather")
        data = ref.get()
        
        if data:
            data_count = len(data)
            data_keys = list(data.keys())
            latest_key = max(data_keys) if data_keys else None
            
            st.success(f"✅ **Firebase Connection Successful!**")
            
            # Show connection metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Records", data_count)
            with col2:
                st.metric("🗓️ Latest Key", latest_key[:10] + "..." if latest_key else "N/A")
            with col3:
                latest_timestamp = data[latest_key].get('timestamp', 'N/A') if latest_key else 'N/A'
                st.metric("⏰ Latest Time", latest_timestamp[:16] if latest_timestamp != 'N/A' else 'N/A')
            
            # Show sample data
            if latest_key:
                with st.expander("📋 Latest Data Sample"):
                    st.json(data[latest_key])
            
            return True
        else:
            st.warning("⚠️ Connected to Firebase but no data found")
            return True
            
    except Exception as e:
        st.error(f"❌ Firebase connection test failed: {e}")
        return False

# === MAIN APPLICATION ===
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
        st.success("🚀 **Running on Streamlit Cloud** with secure secrets")
    else:
        st.info("💻 **Running locally** with firebase_config.json")
    
    # Initialize Firebase
    with st.spinner("Connecting to Firebase..."):
        firebase_initialized = init_firebase()
    
    if not firebase_initialized:
        st.stop()
        
    # Show successful Firebase initialization
    st.success("🔒 Using Streamlit Cloud secrets")
    
    # Fetch data from Firebase
    with st.spinner("Loading weather data from Firebase..."):
        df = fetch_weather_data()
    
    # Check if data is available
    if df.empty:
        st.warning("⚠️ No data available in Firebase.")
        
        st.markdown("""
        **Possible reasons:**
        1. **Backend service is not running**
        2. **No weather data has been collected yet**  
        3. **Database connection issues**
        
        **What to do:**
        - Check if your Flask backend is running
        - Wait for the next data collection cycle
        - Test Firebase connection below
        """)
        
        # Connection test button
        st.subheader("🔧 Diagnostics")
        if st.button("🧪 Test Firebase Connection", type="primary"):
            test_firebase_connection()
        
        return
    
    # Show success message
    st.success(f"✅ Successfully loaded {len(df)} weather data points from Firebase")
    
    # === METRICS OVERVIEW ===
    st.subheader("📊 Latest Metrics")
    
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
        else:
            st.metric("Temp MSE", "N/A")
    
    with col4:
        if 'Wind MSE' in df.columns:
            st.metric("Latest Wind MSE", f"{latest_data['Wind MSE']:.3f}")
        else:
            st.metric("Wind MSE", "N/A")
    
    # === DATA TABLE ===
    st.subheader("📋 Weather Data Table")
    display_df = df.head(20).copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # === TEMPERATURE CHARTS ===
    st.subheader("📈 Temperature: Forecast vs Actual")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['timestamp'], df['Forecast Temp (°C)'], label='Forecast', marker='o', linewidth=2, markersize=4)
    ax.plot(df['timestamp'], df['Actual Temp (°C)'], label='Actual', marker='x', linewidth=2, markersize=6)
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    
    # === TEMPERATURE MSE ===
    if 'Temp MSE' in df.columns:
        st.subheader("📉 Temperature MSE Trend")
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df['timestamp'], df['Temp MSE'], label='Temp MSE', color='red', marker='d', linewidth=2, markersize=4)
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
    ax.plot(df['timestamp'], df['Forecast Wind (km/h)'], label='Forecast', marker='o', linewidth=2, markersize=4)
    ax.plot(df['timestamp'], df['Actual Wind (km/h)'], label='Actual', marker='x', linewidth=2, markersize=6)
    ax.set_xlabel("Time")
    ax.set_ylabel("Wind Speed (km/h)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    
    # === WIND MSE ===
    if 'Wind MSE' in df.columns:
        st.subheader("📉 Wind MSE Trend")
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df['timestamp'], df['Wind MSE'], label='Wind MSE', color='blue', marker='d', linewidth=2, markersize=4)
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
                st.dataframe(temp_stats, use_container_width=True)
        
        with col2:
            st.write("**Wind Statistics:**")
            wind_cols = [col for col in ['Forecast Wind (km/h)', 'Actual Wind (km/h)', 'Wind MSE'] if col in df.columns]
            if wind_cols:
                wind_stats = df[wind_cols].describe().round(3)
                st.dataframe(wind_stats, use_container_width=True)
    
    # === CONTROLS ===
    st.subheader("🔄 Controls")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("🧪 Test Firebase", type="secondary"):
            test_firebase_connection()
    
    # === FOOTER ===
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 14px;'>
            🌤️ IoT Weather Dashboard | 📊 74 Data Points | 🔄 Auto-updates every 5 minutes<br>
            Built with Streamlit & Firebase | 🚀 Deployed on Streamlit Cloud
        </div>
        """, 
        unsafe_allow_html=True
    )

# === RUN APP ===
if __name__ == "__main__":
    main()