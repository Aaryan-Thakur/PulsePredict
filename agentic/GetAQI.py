import requests
import pandas as pd
from datetime import datetime
import os
import time

# --- CONFIGURATION ---
# Delhi Coordinates (Connaught Place)
LAT = 28.61
LON = 77.20
LOG_FILE = "daily_aqi_log.csv"

def calculate_indian_aqi(pm25):
    """
    Converts raw PM2.5 (µg/m³) to Indian AQI (CPCB Standard).
    This logic follows the breakpoints defined by CPCB, India.
    """
    if pm25 <= 30:
        return pm25 * (50/30)
    elif pm25 <= 60:
        return 50 + (pm25 - 30) * (50/30)
    elif pm25 <= 90:
        return 100 + (pm25 - 60) * (100/30)
    elif pm25 <= 120:
        return 200 + (pm25 - 90) * (100/30)
    elif pm25 <= 250:
        return 300 + (pm25 - 120) * (100/130)
    else:
        # Severe (> 250 µg/m³)
        return 400 + (pm25 - 250) * (100/130)

def get_current_month_aqi():
    """
    Fetches raw PM2.5 data and converts to Indian AQI.
    Returns: dictionary with 'Monthly_Avg_AQI' and 'Days_Severe_AQI'
    """
    print(f"🤖 AGENT: Waking up to fetch Air Quality (Indian AQI) for {datetime.now().strftime('%B %Y')}...")

    # 1. Define Timeframe (1st of Month -> Today)
    today = datetime.today().date()
    first_day = today.replace(day=1)
    
    start_str = first_day.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")
    
    print(f"   -> Fetching PM2.5 data from {start_str} to {end_str}...")

    # 2. Build API Request
    # CHANGED: We now fetch 'pm2_5' concentration instead of 'us_aqi'
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "pm2_5",  # Fetch raw PM2.5 concentration
        "timezone": "auto",
        "start_date": start_str,
        "end_date": end_str
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # 3. Process Hourly Data
        hourly_data = data.get('hourly', {})
        timestamps = hourly_data.get('time', [])
        pm25_values = hourly_data.get('pm2_5', [])
        
        if not pm25_values:
            print("   ⚠️ No data returned from API.")
            return {'Monthly_Avg_AQI': 0, 'Days_Severe_AQI': 0}

        # Create DataFrame
        df = pd.DataFrame({
            'time': pd.to_datetime(timestamps),
            'pm25': pm25_values
        })
        
        # 4. Convert to Indian AQI
        # We apply the conversion to every hourly data point
        df['indian_aqi'] = df['pm25'].apply(calculate_indian_aqi)
        
        # 5. Calculate Daily Metrics based on Indian AQI
        df.set_index('time', inplace=True)
        daily_avg_aqi = df['indian_aqi'].resample('D').mean() # Indian AQI uses 24hr Avg
        
        # A. Monthly Average
        monthly_avg = daily_avg_aqi.mean()
        
        # B. Days Severe (Indian Standard: AQI > 400 is Severe)
        severe_days = (daily_avg_aqi > 300).sum() 
        
        results = {
            'Monthly_Avg_AQI': round(monthly_avg, 2),
            'Days_Severe_AQI': int(severe_days)
        }
        
        # 6. Save to CSV
        log_entry = results.copy()
        log_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry['data_source'] = "Open-Meteo (Converted to CPCB)"
        
        df_log = pd.DataFrame([log_entry])
        header = not os.path.exists(LOG_FILE)
        df_log.to_csv(LOG_FILE, mode='a', header=header, index=False)
        
        print(f"✅ Success. Data logged to {LOG_FILE}")
        print(f"   -> Results (Indian Scale): Avg AQI: {results['Monthly_Avg_AQI']}, Severe Days: {results['Days_Severe_AQI']}")
        
        return results

    except Exception as e:
        print(f"   ❌ API Error: {e}")
        return {'Monthly_Avg_AQI': 0, 'Days_Severe_AQI': 0}

if __name__ == "__main__":
    get_current_month_aqi()