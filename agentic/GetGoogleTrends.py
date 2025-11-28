import pandas as pd
import urllib3


if int(urllib3.__version__.split('.')[0]) >= 2:
    from urllib3.util import retry
    class PatchedRetry(retry.Retry):
        def __init__(self, *args, **kwargs):
            if 'method_whitelist' in kwargs:
                kwargs['allowed_methods'] = kwargs.pop('method_whitelist')
            super().__init__(*args, **kwargs)
    retry.Retry = PatchedRetry
# ----------------------------------------------------

from pytrends.request import TrendReq
from datetime import datetime
import time
import os
import random

# --- CONFIGURATION ---
KEYWORDS_LIST = [
    'asthma', 'sore throat', 'cough', 'cold',       # Respiratory
    'dengue',                                       # Vector
    'fever', 'loose motion', 'vomiting', 'stomach pain', # Water/Viral
    'chest pain', 'headache', 'fatigue'             # Acute
]

LOG_FILE = "daily_trends_log.csv"
GEO_LOCATION = 'IN-DL' # Delhi
CATEGORY = 419         # Health Category

def get_current_month_trends():
    """
    Fetches the average interest for the CURRENT month so far.
    Returns a dictionary suitable for model input.
    """
    print(f"🤖 AGENT: Waking up to fetch Google Trends for {datetime.now().strftime('%B %Y')}...")
    
    # 1. Setup Connection
    # We set retries=0 because we are handling retries manually below.
    # The monkey patch above fixes the internal crash.
    pytrends = TrendReq(hl='en-US', tz=330, timeout=(10,25), retries=0, backoff_factor=0.1)
    
    # 2. Define Timeframe (1st of Month -> Today)
    today = datetime.today().date()
    first_day = today.replace(day=1)
    
    # If today is the 1st, use 'now 7-d' (last 7 days) to get *some* signal 
    # otherwise the mean of 0 days is empty.
    if today.day == 1:
        timeframe = 'now 7-d'
        print("   -> It's the 1st of the month. Using last 7 days for signal.")
    else:
        timeframe = f"{first_day} {today}"
        print(f"   -> Timeframe: {timeframe}")

    current_trends = {}

    # 3. Batch Request (Max 5 keywords allowed by Google)
    for i in range(0, len(KEYWORDS_LIST), 5):
        batch = KEYWORDS_LIST[i:i+5]
        print(f"   -> Fetching batch: {batch}")
        
        # --- MANUAL RETRY LOOP ---
        batch_success = False
        for attempt in range(3):
            try:
                pytrends.build_payload(batch, cat=CATEGORY, timeframe=timeframe, geo=GEO_LOCATION)
                data = pytrends.interest_over_time()
                
                if not data.empty:
                    # Drop 'isPartial' column if it exists
                    if 'isPartial' in data.columns:
                        data = data.drop(labels=['isPartial'], axis=1)
                    
                    # CRITICAL STEP: The model needs ONE number (Monthly Avg). 
                    # We take the mean of the daily values retrieved so far.
                    means = data.mean().to_dict()
                    current_trends.update(means)
                else:
                    # If no data, assume 0 (rare for these common terms)
                    for kw in batch:
                        current_trends[kw] = 0.0
                
                batch_success = True
                break # Success! Exit the retry loop

            except Exception as e:
                print(f"   ⚠️ Warning (Attempt {attempt+1}/3): {e}")
                time.sleep(random.uniform(2, 4)) # Wait before retrying
        
        # If all retries failed, fill with 0 to prevent crash
        if not batch_success:
            print(f"   ❌ Failed to fetch batch {batch} after 3 attempts.")
            for kw in batch:
                current_trends[kw] = 0.0

        # Sleep between batches to look human
        time.sleep(random.uniform(2, 5))

    # 4. Save to CSV (Append Mode) - Backup for your Agent
    # We add a timestamp column so you know exactly when this run happened
    log_entry = current_trends.copy()
    log_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    df_log = pd.DataFrame([log_entry])
    
    # Create header if file doesn't exist, otherwise append without header
    header = not os.path.exists(LOG_FILE)
    df_log.to_csv(LOG_FILE, mode='a', header=header, index=False)
    
    print(f"✅ Success. Data logged to {LOG_FILE}")
    print("   -> Current Signals:", current_trends)
    
    return current_trends

if __name__ == "__main__":
    # Test the function
    data = get_current_month_trends()