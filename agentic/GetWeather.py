import requests
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURATION ---
# Delhi Coordinates (Connaught Place)
LAT = 28.61
LON = 77.20
LOG_FILE = "daily_weather_log.csv"

def get_current_month_weather():
    """
    Fetches Temperature, Humidity, and Rainfall for the current month.
    Returns: dictionary with 'Monthly_Avg_Temp', 'Monthly_Avg_Humidity', 'Rainfall_mm'
    """
    print(f"🤖 AGENT: Waking up to fetch Weather Data for {datetime.now().strftime('%B %Y')}...")

    # 1. Define Timeframe (1st of Month -> Today)
    today = datetime.today().date()
    first_day = today.replace(day=1)
    
    start_str = first_day.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")
    
    print(f"   -> Fetching data from {start_str} to {end_str}...")

    # 2. Build API Request
    # We use the Open-Meteo Forecast API which also provides recent history (past days)
    # Parameters needed: Temperature (2m), Humidity (2m), and Rain
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
            return {'Monthly_Avg_Temp': 0, 'Monthly_Avg_Humidity': 0, 'Rainfall_mm': 0}

        # Create DataFrame
        df = pd.DataFrame({
            'time': pd.to_datetime(timestamps),
            'temp': temps,
            'humidity': humidities,
            'rain': rains
        })
        
        # 4. Calculate Aggregates for the Model
        # Temperature & Humidity: We want the AVERAGE for the month so far
        avg_temp = df['temp'].mean()
        avg_humidity = df['humidity'].mean()
        
        # Rainfall: We want the TOTAL SUM for the month so far
        total_rain = df['rain'].sum()
        
        results = {
            'Monthly_Avg_Temp': round(avg_temp, 2),
            'Monthly_Avg_Humidity': round(avg_humidity, 2),
            'Rainfall_mm': round(total_rain, 2)
        }
        
        # 5. Save to CSV
        log_entry = results.copy()
        log_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry['data_source'] = "Open-Meteo Weather API"
        
        df_log = pd.DataFrame([log_entry])
        header = not os.path.exists(LOG_FILE)
        df_log.to_csv(LOG_FILE, mode='a', header=header, index=False)
        
        print(f"✅ Success. Data logged to {LOG_FILE}")
        print(f"   -> Results: Temp: {results['Monthly_Avg_Temp']}°C, Rain: {results['Rainfall_mm']}mm, Humidity: {results['Monthly_Avg_Humidity']}%")
        
        return results

    except Exception as e:
        print(f"   ❌ API Error: {e}")
        return {'Monthly_Avg_Temp': 0, 'Monthly_Avg_Humidity': 0, 'Rainfall_mm': 0}

if __name__ == "__main__":
    get_current_month_weather()