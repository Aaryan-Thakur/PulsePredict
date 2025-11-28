import pandas as pd
import joblib
import os
import sys
from datetime import datetime

# --- 1. ROBUST PATH CONFIGURATION ---
# Get the absolute path of the directory containing THIS file (Pulse Predict/app/)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
AGENTIC_DIR = os.path.join(ROOT_DIR, 'agentic')

# Add paths to system so we can import modules
if AGENTIC_DIR not in sys.path: sys.path.append(AGENTIC_DIR)
if APP_DIR not in sys.path: sys.path.append(APP_DIR)

# --- 2. IMPORT AGENTS ---
try:
    from GetWeather import get_current_month_weather
    from GetAQI import get_current_month_aqi
    from GetGoogleTrends import get_current_month_trends
    from fetch_baseline_rates import get_monthly_baseline
except ImportError as e:
    print(f"❌ CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# --- FILE PATHS ---
MODELS_DIR = os.path.join(ROOT_DIR, "models")
LOG_FILE = os.path.join(ROOT_DIR, "daily_prediction_log.csv")


# ==============================================================================
# 🔹 FUNCTION 1: GATHER INPUTS (The "Senses")
# ==============================================================================
def fetch_all_model_inputs():
    """
    Orchestrates all agents to gather live data.
    Returns: A dictionary containing ALL parameters required by the models.
    """
    print("\n📡 STEP 1: GATHERING LIVE DATA INPUTS...")
    
    # 1. Fetch Raw Data from Agents
    print("   -> Contacting Weather Agent...")
    weather = get_current_month_weather()
    
    print("   -> Contacting AQI Agent...")
    aqi = get_current_month_aqi()
    
    print("   -> Contacting Trends Agent...")
    trends = get_current_month_trends()
    
    print("   -> Contacting Hospital Database (Baseline)...")
    baseline = get_monthly_baseline()

    if not baseline:
        print("   ⚠️ Warning: Baseline data missing. Using 0.0 defaults.")
        baseline = {'Rate_Vector': 0, 'Rate_Respiratory': 0, 'Rate_Water': 0}

    # 2. Consolidate into a Master Input Dictionary
    # This structure is clean and easy for an Agentic AI to read/display
    model_inputs = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # Environmental
        "Monthly_Avg_Temp": weather.get('Monthly_Avg_Temp', 0),
        "Rainfall_mm": weather.get('Rainfall_mm', 0),
        "Rainfall_Lag_2": weather.get('Rainfall_Lag_2', 0),
        "Monthly_Avg_Humidity": weather.get('Monthly_Avg_Humidity', 0),
        "Monthly_Avg_AQI": aqi.get('Monthly_Avg_AQI', 0),
        "Days_Severe_AQI": aqi.get('Days_Severe_AQI', 0),
        
        # Behavioral (Google Trends)
        "dengue": trends.get('dengue', 0),
        "fever": trends.get('fever', 0),
        "asthma": trends.get('asthma', 0),
        "cough": trends.get('cough', 0),
        "cold": trends.get('cold', 0),
        "loose_motion": trends.get('loose motion', 0),
        "vomiting": trends.get('vomiting', 0),
        "stomach_pain": trends.get('stomach pain', 0),
        
        # Hospital Baseline (Current Load Proxy)
        "Rate_Vector_Current": baseline.get('Rate_Vector', 0),
        "Rate_Respiratory_Current": baseline.get('Rate_Respiratory', 0),
        "Rate_Water_Current": baseline.get('Rate_Water', 0)
    }
    
    print("   ✅ Inputs Gathered Successfully.")
    return model_inputs


# ==============================================================================
# 🔹 FUNCTION 2: GENERATE PREDICTIONS (The "Brain")
# ==============================================================================
def generate_forecast(inputs):
    """
    Takes the dictionary from Function 1, feeds it into trained models,
    and returns the prediction results.
    """
    print("\n🧠 STEP 2: RUNNING INFERENCE...")
    
    # 1. Load Models
    models = {}
    model_files = {
        'Rate_Vector': 'Rate_Vector_model.pkl',
        'Rate_Respiratory': 'Rate_Respiratory_model.pkl',
        'Rate_Water': 'Rate_Water_model.pkl'
    }
    
    for key, filename in model_files.items():
        path = os.path.join(MODELS_DIR, filename)
        if os.path.exists(path):
            models[key] = joblib.load(path)
        else:
            print(f"   ⚠️ Model missing: {filename}")

    # 2. Prepare DataFrames (Strict Column Order Required by Sklearn)
    
    # Vector Model Input
    # Features: ['Monthly_Avg_Temp', 'Rainfall_mm', 'Monthly_Avg_Humidity', 'dengue', 'fever', 'Rate_Vector']
    vec_df = pd.DataFrame([{
        'Monthly_Avg_Temp': inputs['Monthly_Avg_Temp'],
        'Rainfall_mm': inputs['Rainfall_mm'],
        'Monthly_Avg_Humidity': inputs['Monthly_Avg_Humidity'],
        'dengue': inputs['dengue'],
        'fever': inputs['fever'],
        'Rate_Vector': inputs['Rate_Vector_Current']
    }])

    # Respiratory Model Input
    # Features: ['Monthly_Avg_AQI', 'Days_Severe_AQI', 'Monthly_Avg_Temp', 'asthma', 'cough', 'cold', 'Rate_Respiratory']
    resp_df = pd.DataFrame([{
        'Monthly_Avg_AQI': inputs['Monthly_Avg_AQI'],
        'Days_Severe_AQI': inputs['Days_Severe_AQI'],
        'Monthly_Avg_Temp': inputs['Monthly_Avg_Temp'],
        'asthma': inputs['asthma'],
        'cough': inputs['cough'],
        'cold': inputs['cold'],
        'Rate_Respiratory': inputs['Rate_Respiratory_Current']
    }])

    # Water Model Input
    # Features: ['Monthly_Avg_Temp', 'Rainfall_mm', 'Rainfall_Lag_2', 'loose motion', 'vomiting', 'stomach pain', 'Rate_Water']
    wat_df = pd.DataFrame([{
        'Monthly_Avg_Temp': inputs['Monthly_Avg_Temp'],
        'Rainfall_mm': inputs['Rainfall_mm'],
        'Rainfall_Lag_2': inputs['Rainfall_Lag_2'],
        'loose motion': inputs['loose_motion'],
        'vomiting': inputs['vomiting'],
        'stomach pain': inputs['stomach_pain'],
        'Rate_Water': inputs['Rate_Water_Current']
    }])

    # 3. Predict
    results = {
        "timestamp": inputs['timestamp']
    }

    # Helper for thresholding
    def get_status(val, threshold):
        return "🔴 SURGE" if val > threshold else "🟢 Normal"

    # Vector Prediction
    if 'Rate_Vector' in models:
        pred = models['Rate_Vector'].predict(vec_df)[0]
        results['Vector_Pred'] = round(pred, 2)
        results['Vector_Status'] = get_status(pred, 1.5)
    else:
        results['Vector_Pred'] = 0.0
        results['Vector_Status'] = "N/A"

    # Respiratory Prediction
    if 'Rate_Respiratory' in models:
        pred = models['Rate_Respiratory'].predict(resp_df)[0]
        results['Respiratory_Pred'] = round(pred, 2)
        results['Resp_Status'] = get_status(pred, 5.0)
    else:
        results['Respiratory_Pred'] = 0.0
        results['Resp_Status'] = "N/A"

    # Water Prediction
    if 'Rate_Water' in models:
        pred = models['Rate_Water'].predict(wat_df)[0]
        results['Water_Pred'] = round(pred, 2)
        results['Water_Status'] = get_status(pred, 4.0)
    else:
        results['Water_Pred'] = 0.0
        results['Water_Status'] = "N/A"

    # 4. Log to CSV
    df_log = pd.DataFrame([results])
    header = not os.path.exists(LOG_FILE)
    df_log.to_csv(LOG_FILE, mode='a', header=header, index=False)
    
    print("   ✅ Forecast Generated & Logged.")
    return results


# ==============================================================================
# 🔹 MAIN EXECUTION (The Glue)
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print(f"🏥 PULSE PREDICT: TWO-STEP SYSTEM RUN")
    print("="*60)
    
    # Step 1: Get Data
    live_inputs = fetch_all_model_inputs()
    
    # (Optional) You can print inputs here to verify what the Agent 'sees'
    print(f"\n👀 AGENT SEES: {live_inputs}")
    
    # Step 2: Get Prediction
    forecast = generate_forecast(live_inputs)
    
    print("\n📢 FINAL REPORT:")
    print(f"   🦟 Vector Risk: {forecast['Vector_Pred']} ({forecast['Vector_Status']})")
    print(f"   🫁 Resp Risk:   {forecast['Respiratory_Pred']} ({forecast['Resp_Status']})")
    print(f"   💧 Water Risk:  {forecast['Water_Pred']} ({forecast['Water_Status']})")