import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# --- CONFIGURATION ---
# Delhi Coordinates (Connaught Place)
LAT = 28.61
LON = 77.20
LOG_FILE = "daily_weather_log.csv"

def get_current_month_weather():
    """
    Fetches Temperature, Humidity, and Rainfall for the current month.
    Also fetches 'Rainfall_Lag_2' (Rainfall from 2 months ago) for the Water-Borne model.
    Returns: dictionary with 'Monthly_Avg_Temp', 'Monthly_Avg_Humidity', 'Rainfall_mm', 'Rainfall_Lag_2'
    """
    print(f"🤖 AGENT: Waking up to fetch Weather Data for {datetime.now().strftime('%B %Y')}...")

    # 1. Define Timeframe (1st of Month -> Today)
    today = datetime.today().date()
    first_day = today.replace(day=1)
    
    start_str = first_day.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")
    
    print(f"   -> Fetching current data from {start_str} to {end_str}...")

    # 2. Build API Request (Current Weather)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "temperature_2m,relative_humidity_2m,rain",
        "timezone": "auto",
        "start_date": start_str,
        "end_date": end_str
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # 3. Process Hourly Data
        hourly = data.get('hourly', {})
        timestamps = hourly.get('time', [])
        temps = hourly.get('temperature_2m', [])
        humidities = hourly.get('relative_humidity_2m', [])
        rains = hourly.get('rain', []) # Rain in mm
        
        if not timestamps:
            print("   ⚠️ No data returned from API.")
            return {'Monthly_Avg_Temp': 0, 'Monthly_Avg_Humidity': 0, 'Rainfall_mm': 0, 'Rainfall_Lag_2': 0}

        # Create DataFrame
        df = pd.DataFrame({
            'time': pd.to_datetime(timestamps),
            'temp': temps,
            'humidity': humidities,
            'rain': rains
        })
        
        # 4. Calculate Aggregates for the Model
        avg_temp = df['temp'].mean()
        avg_humidity = df['humidity'].mean()
        total_rain = df['rain'].sum()
        
        # --- NEW: Fetch Historical Lag Data (2 Months Ago) ---
        # The Water-Borne model needs 'Rainfall_Lag_2'.
        # Logic: If today is Nov, we need Sept rainfall.
        
        # Calculate dates for 2 months ago
        first_current = today.replace(day=1)
        first_prev = (first_current - timedelta(days=1)).replace(day=1) # 1st of Prev Month
        end_lag = (first_prev - timedelta(days=1))                      # Last day of Lag Month
        first_lag = end_lag.replace(day=1)                              # 1st day of Lag Month
        
        start_lag_str = first_lag.strftime("%Y-%m-%d")
        end_lag_str = end_lag.strftime("%Y-%m-%d")
        
        print(f"   -> Fetching historical rain (Lag 2) from {start_lag_str} to {end_lag_str}...")
        
        # Use Archive API for historical data
        url_archive = "https://archive-api.open-meteo.com/v1/archive"
        params_lag = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": "rain",
            "timezone": "auto",
            "start_date": start_lag_str,
            "end_date": end_lag_str
        }
        
        lag_rain = 0.0
        try:
            resp_lag = requests.get(url_archive, params=params_lag)
            resp_lag.raise_for_status()
            data_lag = resp_lag.json()
            rains_lag = data_lag.get('hourly', {}).get('rain', [])
            # Sum filtering out Nones
            if rains_lag:
                lag_rain = sum(r for r in rains_lag if r is not None)
        except Exception as e:
            print(f"   ⚠️ Error fetching lag data: {e}")
            # We default to 0.0 if history fetch fails, so the model doesn't crash
        
        results = {
            'Monthly_Avg_Temp': round(avg_temp, 2),
            'Monthly_Avg_Humidity': round(avg_humidity, 2),
            'Rainfall_mm': round(total_rain, 2),
            'Rainfall_Lag_2': round(lag_rain, 2) # <--- Added Lag Feature
        }
        
        # 5. Save to CSV
        log_entry = results.copy()
        log_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry['data_source'] = "Open-Meteo Weather API"
        
        df_log = pd.DataFrame([log_entry])
        header = not os.path.exists(LOG_FILE)
        df_log.to_csv(LOG_FILE, mode='a', header=header, index=False)
        
        print(f"✅ Success. Data logged to {LOG_FILE}")
        print(f"   -> Results: Temp: {results['Monthly_Avg_Temp']}°C, Rain: {results['Rainfall_mm']}mm, Humidity: {results['Monthly_Avg_Humidity']}%,Lag Rain: {results['Rainfall_Lag_2']}mm")
        
        return results

    except Exception as e:
        print(f"   ❌ API Error: {e}")
        return {'Monthly_Avg_Temp': 0, 'Monthly_Avg_Humidity': 0, 'Rainfall_mm': 0, 'Rainfall_Lag_2': 0}

if __name__ == "__main__":
    get_current_month_weather()