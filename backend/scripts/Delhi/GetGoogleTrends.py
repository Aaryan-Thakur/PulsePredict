# Save this as fetch_trends_v2.py
import pandas as pd
from pytrends.request import TrendReq
import time
import os
def fetch_monthly_trends(keywords, start_year=2017, end_year=2019):
    # hl='en-US' is fine, but 'tz=330' ensures Indian Standard Time alignment
    pytrends = TrendReq(hl='en-US', tz=330) 
    
    all_data = pd.DataFrame()
    
    # Google Trends allows max 5 keywords at a time.
    for i in range(0, len(keywords), 5):
        batch = keywords[i:i+5]
        print(f"Fetching batch: {batch}")
        
        pytrends.build_payload(batch, cat=419, timeframe=f'{start_year}-01-01 {end_year}-12-31', geo='IN-DL')
        
        data = pytrends.interest_over_time()
        if not data.empty:
            data = data.drop(labels=['isPartial'], axis=1)
            all_data = pd.concat([all_data, data], axis=1)
        
        # Sleep to avoid getting blocked
        time.sleep(5)
        
    # Resample to monthly mean to smooth out daily volatility
    all_data = all_data.resample('MS').mean()
    return all_data

# --- KEY CHANGE 2: Behavioral Keywords (Indian Context) ---
keywords_list = [
    # --- Respiratory (The Delhi Smog Signals) ---
    'asthma',             # Chronic trigger
    'sore throat',        # Early smog symptom
    'cough',
    'cold',

    # --- Vector Borne (The Panic Signals) ---
    'dengue',

    # --- General / Viral / Water Borne ---
    'fever',
    'loose motion',
    'vomiting',
    'stomach pain',

    # --- Critical / Acute ---
    'chest pain',         # Pollution triggers heart attacks
    'headache',
    'fatigue'
]

print("Connecting to Google Trends (Health Category)...")
df_trends = fetch_monthly_trends(keywords_list, 2017, 2019)

# Clean up columns (lowercase everything)
df_trends.columns = df_trends.columns.str.lower()
output_filename = 'Delhi_Google_Trends_Health.csv'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", output_filename))
# Save
df_trends.to_csv(OUTPUT_FILE)
print(df_trends.head())