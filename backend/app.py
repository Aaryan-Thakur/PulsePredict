import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="PulsePredict Command Center",
    page_icon="🏥",
    layout="wide"
)

# --- LOAD MODELS ---
# We use st.cache_resource so we only load these once!
@st.cache_resource
def load_models():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, "models")
    
    models = {}
    model_files = {
        'Rate_Vector': 'Rate_Vector_model.pkl',
        'Rate_Respiratory': 'Rate_Respiratory_model.pkl',
        'Rate_Water': 'Rate_Water_model.pkl'
    }
    
    for key, filename in model_files.items():
        path = os.path.join(models_dir, filename)
        if os.path.exists(path):
            models[key] = joblib.load(path)
        else:
            st.error(f"⚠️ Model file not found: {filename}. Please run training script first.")
            return None
    return models

models = load_models()

# --- SIDEBAR: ENVIRONMENTAL CONTROLS ---
st.sidebar.header("🌍 Environmental Conditions")
st.sidebar.markdown("Simulate next month's weather:")

# Weather Sliders
avg_temp = st.sidebar.slider("Avg Temperature (°C)", 5.0, 45.0, 30.0)
rainfall = st.sidebar.slider("Total Rainfall (mm)", 0.0, 400.0, 120.0)
humidity = st.sidebar.slider("Avg Humidity (%)", 10.0, 100.0, 65.0)

# The "Secret Weapon" Slider (Lag Feature)
st.sidebar.markdown("---")
st.sidebar.markdown("**💧 History (Lag Factors)**")
rain_lag_2 = st.sidebar.slider("Rainfall (2 Months Ago)", 0.0, 400.0, 50.0, 
                               help="High rain 2 months ago contaminates groundwater today.")

st.sidebar.markdown("---")
st.sidebar.markdown("**🌫️ Pollution Control**")
aqi = st.sidebar.slider("Avg AQI", 50.0, 500.0, 150.0)
days_severe = st.sidebar.slider("Days with Severe AQI", 0, 30, 2)

# --- MAIN DASHBOARD ---
st.title("🏥 Hospital Surge Model Demo Dashboard")
st.markdown("Adjust the sliders to simulate future outbreaks and resource needs.")

# Create 3 Columns for Layout
col1, col2, col3 = st.columns(3)

# --- GOOGLE TRENDS INPUTS (BEHAVIORAL) ---
with st.expander("🔎 Google Search Trends (Symptom Tracking)", expanded=True):
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    # Vector
    trend_dengue = t_col1.slider("Search: 'Dengue'", 0, 100, 15)
    trend_fever = t_col2.slider("Search: 'Fever'", 0, 100, 35)
    # Respiratory
    trend_cough = t_col3.slider("Search: 'Cough'", 0, 100, 25)
    trend_asthma = t_col4.slider("Search: 'Asthma'", 0, 100, 10)
    trend_cold = t_col1.slider("Search: 'Cold'", 0, 100, 15)
    # Water
    trend_loose = t_col2.slider("Search: 'Loose Motion'", 0, 100, 12)
    trend_vomit = t_col3.slider("Search: 'Vomiting'", 0, 100, 10)
    trend_stomach = t_col4.slider("Search: 'Stomach Pain'", 0, 100, 20)

# --- CURRENT HOSPITAL STATE ---
with st.expander("🏥 Current Hospital Load (Baseline)", expanded=False):
    h_col1, h_col2, h_col3 = st.columns(3)
    curr_vector = h_col1.slider("Current Vector Cases / 1k", 0.0, 5.0, 0.8)
    curr_resp = h_col2.slider("Current Resp. Cases / 1k", 0.0, 10.0, 2.5)
    curr_water = h_col3.slider("Current Water Cases / 1k", 0.0, 10.0, 3.0)

# --- PREDICTION LOGIC ---
if models:
    # 1. VECTOR MODEL PREDICTION
    # Features: ['Monthly_Avg_Temp', 'Rainfall_mm', 'Monthly_Avg_Humidity', 'dengue', 'fever', 'Rate_Vector']
    vec_input = pd.DataFrame([[avg_temp, rainfall, humidity, trend_dengue, trend_fever, curr_vector]], 
                             columns=['Monthly_Avg_Temp', 'Rainfall_mm', 'Monthly_Avg_Humidity', 'dengue', 'fever', 'Rate_Vector'])
    vec_pred = models['Rate_Vector'].predict(vec_input)[0]

    # 2. RESPIRATORY MODEL PREDICTION
    # Features: ['Monthly_Avg_AQI', 'Days_Severe_AQI', 'Monthly_Avg_Temp', 'asthma', 'cough', 'cold', 'Rate_Respiratory']
    resp_input = pd.DataFrame([[aqi, days_severe, avg_temp, trend_asthma, trend_cough, trend_cold, curr_resp]], 
                              columns=['Monthly_Avg_AQI', 'Days_Severe_AQI', 'Monthly_Avg_Temp', 'asthma', 'cough', 'cold', 'Rate_Respiratory'])
    resp_pred = models['Rate_Respiratory'].predict(resp_input)[0]

    # 3. WATER MODEL PREDICTION
    # Features: ['Monthly_Avg_Temp', 'Rainfall_mm', 'Rainfall_Lag_2', 'loose motion', 'vomiting', 'stomach pain', 'Rate_Water']
    wat_input = pd.DataFrame([[avg_temp, rainfall, rain_lag_2, trend_loose, trend_vomit, trend_stomach, curr_water]], 
                             columns=['Monthly_Avg_Temp', 'Rainfall_mm', 'Rainfall_Lag_2', 'loose motion', 'vomiting', 'stomach pain', 'Rate_Water'])
    wat_pred = models['Rate_Water'].predict(wat_input)[0]

    # --- DISPLAY RESULTS ---
    st.markdown("---")
    st.subheader("🔮 AI Forecast for Next Month")

    res_col1, res_col2, res_col3 = st.columns(3)

    # Helper function for metrics
    def display_card(column, title, value, threshold, unit="cases/1k"):
        is_surge = value > threshold
        delta_color = "inverse" if is_surge else "normal" # Red if surge (inverse of good)
        status = "🔴 SURGE DETECTED" if is_surge else "🟢 Normal Capacity"
        
        column.metric(label=title, value=f"{value:.2f}", delta=status, delta_color=delta_color)
        
        if is_surge:
            column.warning("⚠️ Mobilize Extra Staff")
        else:
            column.success("✅ Standard Operations")

    # Vector Card
    with res_col1:
        st.markdown("### 🦟 Vector-Borne")
        st.caption("Dengue, Malaria")
        display_card(st, "Predicted Rate", vec_pred, threshold=1.5)
        # Context
        st.progress(min(vec_pred/3.0, 1.0)) # Bar chart visual

    # Respiratory Card
    with res_col2:
        st.markdown("### 🫁 Respiratory")
        st.caption("Asthma, COPD")
        display_card(st, "Predicted Rate", resp_pred, threshold=5.0)
        st.progress(min(resp_pred/8.0, 1.0))

    # Water Card
    with res_col3:
        st.markdown("### 💧 Water-Borne")
        st.caption("Typhoid, Diarrhea")
        display_card(st, "Predicted Rate", wat_pred, threshold=4.0)
        st.progress(min(wat_pred/7.0, 1.0))

else:
    st.warning("Models not loaded. Please ensure training script ran successfully.")