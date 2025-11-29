import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to your TRAINING DATA (The Source of Truth)
DATA_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "final", "Delhi_Master_Dataset.csv"))

def get_monthly_baseline():
    """
    Calculates the average historical disease rates for the CURRENT month.
    Used as a fallback when live hospital data is unavailable (Day 0).
    """
    current_month_name = datetime.now().strftime('%B')
    current_month_idx = datetime.now().month  # 1 = Jan, 11 = Nov
    
    print(f"🤖 AGENT: Calculating Historical Baseline Rates for {current_month_name}...")
    
    try:
        df = pd.read_csv(DATA_FILE)
        
        # 1. Convert Date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # 2. Filter for ONLY the current month (across all years 2017-2019)
        # e.g., Get all rows where Month == 11
        month_data = df[df['Date'].dt.month == current_month_idx]
        
        if month_data.empty:
            print(f"   ⚠️ No historical data found for {current_month_name}!")
            return None

        # 3. Calculate Averages
        # These are your "Safe Defaults"
        avg_vector = month_data['Rate_Vector'].mean()
        avg_respiratory = month_data['Rate_Respiratory'].mean()
        avg_water = month_data['Rate_Water'].mean()
        
        results = {
            'Rate_Vector': round(avg_vector, 2),
            'Rate_Respiratory': round(avg_respiratory, 2),
            'Rate_Water': round(avg_water, 2)
        }
        
        print(f"   -> Historical Average for {current_month_name}:")
        print(f"      🦟 Vector: {results['Rate_Vector']} (cases/1k)")
        print(f"      🫁 Resp:   {results['Rate_Respiratory']} (cases/1k)")
        print(f"      💧 Water:  {results['Rate_Water']} (cases/1k)")
        
        return results

    except FileNotFoundError:
        print(f"   ❌ Error: Master Dataset not found at {DATA_FILE}")
        return {'Rate_Vector': 0.0, 'Rate_Respiratory': 0.0, 'Rate_Water': 0.0}

if __name__ == "__main__":
    get_monthly_baseline()