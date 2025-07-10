from flask import Flask
import requests
from datetime import datetime
import schedule
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# === CONFIGURATION ===
LATITUDE = "3.139"
LONGITUDE = "101.6869"
TIMEZONE = "Asia/Kuala_Lumpur"

FORECAST_URL = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&hourly=temperature_2m,wind_speed_10m&timezone={TIMEZONE}"
CURRENT_URL = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,wind_speed_10m&timezone={TIMEZONE}"

# === FIREBASE SETUP ===
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://weathering-app-iot-default-rtdb.firebaseio.com/'
})

def fetch_and_store():
    print("\n[DEBUG] Fetching weather data...")

    forecast_res = requests.get(FORECAST_URL)
    current_res = requests.get(CURRENT_URL)

    print("[DEBUG] Forecast status:", forecast_res.status_code)
    print("[DEBUG] Current status:", current_res.status_code)

    if forecast_res.status_code != 200:
        print("[ERROR] Forecast API failed!")
        return

    if current_res.status_code != 200:
        print("[ERROR] Current API failed!")
        return

    forecast_json = forecast_res.json()
    current_json = current_res.json()

    # Timestamp untuk storage — ikut waktu sebenar (bukan round ke jam)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # Cari hour_str untuk padan dengan forecast API
    hour_str = now.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")

    try:
        forecast_times = forecast_json['hourly']['time']

        if hour_str not in forecast_times:
            print(f"[WARNING] Forecast data for {hour_str} not found. Skipping.")
            return

        hour_index = forecast_times.index(hour_str)
        temp_forecast = forecast_json['hourly']['temperature_2m'][hour_index]
        wind_forecast = forecast_json['hourly']['wind_speed_10m'][hour_index]

        temp_actual = current_json['current']['temperature_2m']
        wind_actual = current_json['current']['wind_speed_10m']

        temp_mse = (temp_actual - temp_forecast) ** 2
        wind_mse = (wind_actual - wind_forecast) ** 2

        # === Save to Firebase ===
        ref = db.reference("weather")
        ref.push({
            'timestamp': timestamp,
            'temp_forecast': temp_forecast,
            'temp_actual': temp_actual,
            'wind_forecast': wind_forecast,
            'wind_actual': wind_actual,
            'temp_mse': temp_mse,
            'wind_mse': wind_mse
        })

        print(f"[✅] Data stored in Firebase at {timestamp}")
        print(f"[INFO] Temp Forecast: {temp_forecast}, Actual: {temp_actual}")
        print(f"[INFO] Wind Forecast: {wind_forecast}, Actual: {wind_actual}")
        print(f"[INFO] Temp MSE: {temp_mse:.4f}, Wind MSE: {wind_mse:.4f}")

    except Exception as e:
        print(f"[ERROR] Data processing or storing failed: {e}")

@app.route("/ping", methods=["GET"])
def ping():
    return "Firebase Weather Logger is running!"

def run_scheduler():
    schedule.every(1).minutes.do(fetch_and_store)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=run_scheduler).start()
    app.run(debug=True, port=5001)
