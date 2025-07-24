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
        error_msg = str(e)
        if "Invalid JWT Signature" in error_msg:
            st.error("🔑 **CRITICAL: Invalid Firebase Service Account Key**")
            st.markdown("""
            **Your Firebase key is invalid/expired. Fix this NOW:**
            
            1. 🔑 **Generate New Key**: Go to Firebase Console → Project Settings → Service Accounts → Generate New Private Key
            2. 🗑️ **Delete Old Key**: Remove the current invalid key from Firebase Console  
            3. 🔄 **Update Secrets**: Replace your Streamlit Cloud secrets with the new key
            4. ⏳ **Wait**: Allow 2-3 minutes for the app to restart
            
            **⚠️ Security Note**: Your current key may be compromised - replace it immediately!
            """)
        else:
            st.error(f"❌ Firebase initialization failed: {e}")
        return False

# === IMPROVED FIREBASE DATA FETCHING ===
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_firebase_data():
    """Fetch weather data from Firebase with comprehensive error handling"""
    try:
        ref = db.reference("weather")
        data = ref.get()
        
        if data is None:
            return None
        
        if not isinstance(data, dict):
            st.warning("⚠️ Unexpected data format from Firebase")
            return None
        
        return data
        
    except Exception as e:
        error_msg = str(e)
        
        if "invalid jwt signature" in error_msg.lower():
            st.error("🔑 **Authentication Failed**: Service account key is invalid")
        elif "permission denied" in error_msg.lower():
            st.error("🚫 **Access Denied**: Check Firebase database rules")
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            st.error("🌐 **Network Error**: Check internet connection")
        else:
            st.error(f"❌ Firebase Error: {error_msg}")
        
        return None

# === IMPROVED CONNECTION TEST ===
def test_firebase_connection():
    """Test Firebase connection with detailed diagnostics"""
    with st.spinner("Testing Firebase connection..."):
        try:
            ref = db.reference("weather")
            
            # Test basic connection
            all_data = ref.get()
            
            if all_data:
                # Process the data
                data_count = len(all_data)
                data_keys = list(all_data.keys())
                latest_key = max(data_keys) if data_keys else None
                
                st.success("✅ **Firebase Connection Successful!**")
                
                # Show connection details
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Total Records", data_count)
                with col2:
                    st.metric("🗓️ Latest Key", latest_key[:10] + "..." if latest_key else "N/A")
                with col3:
                    latest_timestamp = all_data[latest_key].get('timestamp', 'N/A') if latest_key else 'N/A'
                    st.metric("⏰ Latest Time", latest_timestamp[:16] if latest_timestamp != 'N/A' else 'N/A')
                
                # Show sample data
                if latest_key:
                    with st.expander("📋 Latest Data Sample"):
                        st.json(all_data[latest_key])
                
                return True
                
            else:
                st.warning("⚠️ **Connected but No Data Found**")
                st.info("Firebase connection works, but no weather data has been collected yet.")
                st.markdown("""
                **This usually means:**
                - Your backend service hasn't started collecting data
                - Data collection is scheduled but hasn't run yet
                - Database is empty (first time setup)
                
                **What to do:**
                - Check if your Flask backend is running
                - Wait for the next hourly data collection
                - Manually trigger data collection if possible
                """)
                return True
                
        except Exception as e:
            st.error(f"❌ **Connection Test Failed**")
            
            error_msg = str(e).lower()
            if "invalid jwt signature" in error_msg:
                st.error("🔑 **Invalid Service Account Key**")
                st.markdown("""
                **URGENT: Generate a new Firebase service account key:**
                1. Firebase Console → Project Settings → Service Accounts
                2. Click "Generate New Private Key"  
                3. Update your Streamlit Cloud secrets
                4. Delete the old/invalid key from Firebase Console
                """)
            elif "permission denied" in error_msg:
                st.error("🚫 **Permission Denied**")
                st.info("Check Firebase database security rules and service account permissions")
            elif "network" in error_msg or "connection" in error_msg:
                st.error("🌐 **Network Issue**")
                st.info("Check your internet connection and Firebase service status")
            else:
                st.error(f"🔧 **Technical Error**: {e}")
            
            return False

# === DATA PROCESSING ===
def process_data(data):
    """Convert Firebase data to DataFrame with error handling"""
    if not data:
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(list(data.values()))
        
        # Check for required columns
        required_cols = ['timestamp', 'temp_actual', 'temp_forecast', 'wind_actual', 'wind_forecast']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Missing required data columns: {missing_cols}")
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
        st.error(f"❌ Error processing data: {e}")
        return pd.DataFrame()

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
    firebase_initialized = init_firebase()
    
    if not firebase_initialized:
        st.stop()
        
    # Show successful Firebase initialization
    st.success("🔒 Using Streamlit Cloud secrets")
    
    # Fetch data from Firebase
    with st.spinner("Loading weather data from Firebase..."):
        data = fetch_firebase_data()
    
    # Process data
    df = process_data(data)
    
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
    
    # === TEMPERATURE MSE ===
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
    
    # === WIND MSE ===
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

# === RUN APP ===
if __name__ == "__main__":
    main()