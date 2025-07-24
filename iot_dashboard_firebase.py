import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, db
import json
import os
import traceback

# === STREAMLIT CLOUD FIREBASE SETUP ===
@st.cache_resource
def init_firebase():
    """Initialize Firebase with detailed debugging"""
    st.write("🔄 **Step 1: Starting Firebase initialization...**")
    
    try:
        if not firebase_admin._apps:
            st.write("🔄 **Step 2: No existing Firebase apps found, creating new connection...**")
            
            # Check for Streamlit secrets
            if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                st.write("🔄 **Step 3: Found Streamlit secrets, building config...**")
                
                # Build Firebase config from secrets
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
                
                st.write(f"🔄 **Step 4: Config built for project: {firebase_config['project_id']}**")
                st.write(f"🔄 **Step 5: Database URL: {database_url}**")
                
            elif os.path.exists("firebase_config.json"):
                st.write("🔄 **Step 3: Using local firebase_config.json...**")
                with open("firebase_config.json", 'r') as f:
                    firebase_config = json.load(f)
                database_url = "https://weathering-app-iot-default-rtdb.firebaseio.com/"
                
            else:
                st.error("❌ **Step 3 FAILED: No Firebase configuration found!**")
                return False

            st.write("🔄 **Step 6: Creating Firebase credentials...**")
            cred = credentials.Certificate(firebase_config)
            
            st.write("🔄 **Step 7: Initializing Firebase app...**")
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
            st.success("✅ **Step 8: Firebase initialized successfully!**")
            return True
        else:
            st.write("ℹ️ **Firebase app already exists, using existing connection**")
            return True
            
    except Exception as e:
        st.error(f"❌ **Firebase initialization FAILED at some step**")
        st.error(f"**Error details:** {str(e)}")
        st.code(traceback.format_exc())
        return False

# === DEBUG DATA FETCHING ===
def fetch_firebase_data_debug():
    """Fetch data with step-by-step debugging"""
    st.write("🔄 **Step A: Starting data fetch from Firebase...**")
    
    try:
        st.write("🔄 **Step B: Getting database reference...**")
        ref = db.reference("weather")
        
        st.write("🔄 **Step C: Calling ref.get()...**")
        data = ref.get()
        
        st.write("🔄 **Step D: Data fetch completed**")
        
        if data is None:
            st.warning("⚠️ **Step E: Data is None (empty database)**")
            return None
        elif not isinstance(data, dict):
            st.warning(f"⚠️ **Step E: Unexpected data type: {type(data)}**")
            return None
        else:
            st.success(f"✅ **Step E: Successfully got {len(data)} records**")
            st.write(f"📊 **Sample keys:** {list(data.keys())[:3]}...")
            return data
        
    except Exception as e:
        st.error(f"❌ **Data fetch FAILED**")
        st.error(f"**Error details:** {str(e)}")
        st.code(traceback.format_exc())
        return None

# === SIMPLE CONNECTION TEST ===
def simple_connection_test():
    """Simple Firebase connection test"""
    st.write("🧪 **Testing Firebase Connection...**")
    
    try:
        ref = db.reference("weather")
        data = ref.get()
        
        if data:
            st.success(f"✅ **Connection successful! Found {len(data)} records**")
            
            # Show first record as sample
            first_key = list(data.keys())[0]
            first_record = data[first_key]
            
            st.write("📋 **Sample Record:**")
            st.json(first_record)
            
        else:
            st.warning("⚠️ **Connected but no data found**")
            
    except Exception as e:
        st.error(f"❌ **Connection test failed: {e}**")
        st.code(traceback.format_exc())

# === MAIN APPLICATION WITH DEBUGGING ===
def main():
    # Page configuration
    st.set_page_config(
        page_title="Debug IoT Weather Dashboard",
        page_icon="🌤️",
        layout="wide"
    )
    
    # Title
    st.title("🌤️ IoT Weather Dashboard (Firebase) - DEBUG MODE")
    st.write("Forecast vs Actual Comparison & MSE")
    
    # Show deployment status
    if hasattr(st, 'secrets') and 'firebase' in st.secrets:
        st.success("🚀 **Running on Streamlit Cloud** with secure secrets")
    else:
        st.info("💻 **Running locally** with firebase_config.json")
    
    st.write("---")
    st.subheader("🔍 Debug Information")
    
    # Step 1: Initialize Firebase with debugging
    st.write("## 🔥 Firebase Initialization")
    firebase_initialized = init_firebase()
    
    if not firebase_initialized:
        st.error("🛑 **STOPPED: Firebase initialization failed**")
        st.stop()
    
    st.write("---")
    
    # Step 2: Test basic connection
    st.write("## 🧪 Connection Test")
    if st.button("🧪 Test Firebase Connection Now", type="primary"):
        simple_connection_test()
    
    st.write("---")
    
    # Step 3: Fetch data with debugging
    st.write("## 📊 Data Fetching")
    
    if st.button("📥 Fetch Data from Firebase", type="secondary"):
        data = fetch_firebase_data_debug()
        
        if data:
            st.success("✅ **Data fetch successful!**")
            
            # Try to process the data
            st.write("🔄 **Processing data into DataFrame...**")
            try:
                df = pd.DataFrame(list(data.values()))
                st.success(f"✅ **DataFrame created with {len(df)} rows and {len(df.columns)} columns**")
                st.write("**Columns found:**", list(df.columns))
                
                # Show sample data
                st.write("**Sample data:**")
                st.dataframe(df.head(3))
                
            except Exception as e:
                st.error(f"❌ **DataFrame processing failed: {e}**")
                st.code(traceback.format_exc())
        else:
            st.warning("⚠️ **No data returned from Firebase**")
    
    st.write("---")
    
    # Step 4: Environment info
    st.write("## ⚙️ Environment Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Python packages:**")
        try:
            import firebase_admin
            st.write(f"✅ firebase-admin: {firebase_admin.__version__}")
        except:
            st.write("❌ firebase-admin: Not available")
            
        try:
            import pandas as pd
            st.write(f"✅ pandas: {pd.__version__}")
        except:
            st.write("❌ pandas: Not available")
    
    with col2:
        st.write("**Streamlit info:**")
        st.write(f"✅ Streamlit version: {st.__version__}")
        st.write(f"✅ Secrets available: {hasattr(st, 'secrets')}")
        if hasattr(st, 'secrets'):
            st.write(f"✅ Firebase secrets: {'firebase' in st.secrets}")
            st.write(f"✅ Database secrets: {'database' in st.secrets}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ **CRITICAL ERROR in main()**: {e}")
        st.code(traceback.format_exc())