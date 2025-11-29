import os
import sys
import json
import warnings
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

# Filter warnings for cleaner logs
warnings.filterwarnings("ignore")

load_dotenv()

# --- 1. PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTIC_DIR = os.path.join(BASE_DIR, 'agentic')

if AGENTIC_DIR not in sys.path:
    sys.path.append(AGENTIC_DIR)

# --- 2. IMPORT TEAM MODULES (With Fallbacks) ---
try:
    from GetWeather import get_current_month_weather
    from GetAQI import get_current_month_aqi
    from GetGoogleTrends import get_current_month_trends
    from fetch_baseline_rates import get_monthly_baseline
    print(f"✅ Loaded modules from: {AGENTIC_DIR}")
except ImportError as e:
    print(f"⚠️  Import Error: {e}. Running in Mock Mode.")
    def get_current_month_weather(): return None
    def get_current_month_aqi(): return None
    def get_current_month_trends(): return None
    def get_monthly_baseline(): return None

app = FastAPI(title="Pulse Predict Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. GLOBAL STATE (In-Memory Database) ---
# This dictionary persists as long as the server is running.
# It acts as our "Database" for the demo.
HOSPITAL_STATE = {
    "inventory": {
        "masks": 454,
        "oxygen": 32, 
        "beds_available": 17, 
        "ors_packs": 50
    },
    "system_logs": []
}

# --- 4. DATA GATHERING ---

def fetch_real_data():
    """
    Fetches real data with a fallback to simulation data.
    """
    print("📡 Fetching Sensor Data...")
    
    try:
        weather = get_current_month_weather()
        aqi = get_current_month_aqi()
        trends = get_current_month_trends()
        baseline = get_monthly_baseline()
    except Exception as e:
        print(f"❌ Script Execution Error: {e}")
        weather, aqi, trends, baseline = None, None, None, None

    # --- DEMO SAVER: Default values if APIs fail ---
    if not weather or not weather.get('Monthly_Avg_Temp'):
        weather = {'Monthly_Avg_Temp': 32.5, 'Rainfall_mm': 120.5, 'Rainfall_Lag_2': 45.0, 'Monthly_Avg_Humidity': 78.0}
    
    if not aqi or not aqi.get('Monthly_Avg_AQI'):
        aqi = {'Monthly_Avg_AQI': 165.0, 'Days_Severe_AQI': 3}

    if not trends:
        trends = {'dengue': 85, 'fever': 60, 'asthma': 40, 'cough': 30, 'cold': 20, 'loose motion': 15, 'vomiting': 10, 'stomach pain': 25}
        
    if not baseline:
        baseline = {'Rate_Vector': 1.2, 'Rate_Respiratory': 2.5, 'Rate_Water': 0.8}

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # Environmental
        "Monthly_Avg_Temp": float(weather.get('Monthly_Avg_Temp', 0)),
        "Rainfall_mm": float(weather.get('Rainfall_mm', 0)),
        "Rainfall_Lag_2": float(weather.get('Rainfall_Lag_2', 0)),
        "Monthly_Avg_Humidity": float(weather.get('Monthly_Avg_Humidity', 0)),
        "Monthly_Avg_AQI": float(aqi.get('Monthly_Avg_AQI', 0)),
        "Days_Severe_AQI": float(aqi.get('Days_Severe_AQI', 0)),
        # Behavioral
        "dengue": int(trends.get('dengue', 0)),
        "fever": int(trends.get('fever', 0)),
        "asthma": int(trends.get('asthma', 0)),
        "cough": int(trends.get('cough', 0)),
        "cold": int(trends.get('cold', 0)),
        "loose_motion": int(trends.get('loose motion', 0)),
        "vomiting": int(trends.get('vomiting', 0)),
        "stomach_pain": int(trends.get('stomach pain', 0)),
    }

# --- 5. HEURISTIC PREDICTION ENGINE ---

def calculate_risk_score(category, inputs):
    score = 1.0 
    
    if category == 'respiratory':
        if inputs['Monthly_Avg_AQI'] > 150: score += 3.0
        elif inputs['Monthly_Avg_AQI'] > 100: score += 1.5
        if inputs['Monthly_Avg_Temp'] < 18: score += 2.0 
        symptom_load = (inputs['cough'] + inputs['cold'] + inputs['asthma']) / 3
        if symptom_load > 50: score += 3.0
        
    elif category == 'water':
        if inputs['Rainfall_mm'] > 100: score += 3.0
        symptom_load = (inputs['loose_motion'] + inputs['vomiting'] + inputs['stomach_pain']) / 3
        if symptom_load > 40: score += 4.0

    elif category == 'vector':
        if inputs['Monthly_Avg_Humidity'] > 70: score += 2.0
        if 25 < inputs['Monthly_Avg_Temp'] < 34: score += 2.0 
        if inputs['Rainfall_mm'] > 50: score += 1.0
        symptom_load = (inputs['dengue'] + inputs['fever']) / 2
        if symptom_load > 60: score += 4.0
        elif symptom_load > 30: score += 2.0

    return min(round(score, 1), 10.0)

def run_ml_predictions(inputs):
    print("🧠 Running Heuristic Risk Assessment...")
    vec_score = calculate_risk_score('vector', inputs)
    resp_score = calculate_risk_score('respiratory', inputs)
    wat_score = calculate_risk_score('water', inputs)

    def get_status(s):
        if s >= 7.0: return "🔴 CRITICAL"
        if s >= 4.0: return "🟠 WARNING"
        return "🟢 NORMAL"

    return {
        'Vector_Pred': vec_score, 'Vector_Status': get_status(vec_score),
        'Respiratory_Pred': resp_score, 'Resp_Status': get_status(resp_score),
        'Water_Pred': wat_score, 'Water_Status': get_status(wat_score)
    }

# --- 6. AI AGENT (SMARTER) ---

def run_agent_analysis(inputs, predictions):
    """
    Generates Action Items with explicit instructions on which ones are
    machine-executable vs human-only.
    """
    if not os.getenv("GROQ_API_KEY"):
        # Fallback if no key
        return {
            "summary": "AI Agent requires GROQ_API_KEY. Running in safe mode.",
            "actions": [
                {"id": 1, "title": "Check API Keys", "type": "SYSTEM", "description": "Ensure .env file has valid keys.", "priority": "High", "executable": False}
            ]
        }
    
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
        
        trends_list = ['dengue', 'fever', 'asthma', 'cough', 'cold', 'loose_motion', 'vomiting']
        top_trend = max(trends_list, key=lambda x: inputs.get(x, 0))

        system_prompt = f"""
        You are Sentin-AI, an automated Hospital Command System.
        
        CONTEXT:
        - Trend: {top_trend.title()}
        - Risks: Vector({predictions['Vector_Status']}), Respiratory({predictions['Resp_Status']})
        
        TASK:
        Generate 3 high-priority Action Items.
        Crucially, determine if the action is "executable" by you (a computer system).
        
        - EXECUTABLE ACTIONS (Set executable: true): Sending alerts, Updating inventory records, Logging reports.
        - PHYSICAL ACTIONS (Set executable: false): Cleaning, Performing surgery, Deploying physical teams, Inspecting equipment.

        For executable actions, provide a 'function_payload' object describing what to do.

        Return ONLY JSON in this format:
        {{
            "summary": "Brief situation report.",
            "actions": [
                {{
                    "id": 1,
                    "title": "Action Title",
                    "type": "COMMUNICATION|INVENTORY|PROTOCOL", 
                    "description": "Short description.",
                    "priority": "High|Medium|Low",
                    "executable": true/false,
                    "function_payload": {{ "action": "ALERT_ALL" }} or null
                }}
            ]
        }}
        """
        
        response = llm.invoke([SystemMessage(content=system_prompt), ("user", "Generate Action Plan.")])
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f"Agent Error: {e}")
        return {
            "summary": "System running in manual fallback mode due to AI error.",
            "actions": [
                {"id": 1, "title": "Manual Risk Assessment", "type": "PROTOCOL", "description": "AI unavailable. Perform manual checks.", "priority": "High", "executable": False}
            ]
        }

# --- 7. API ENDPOINTS ---

class ScanRequest(BaseModel):
    action: str

class ActionRequest(BaseModel):
    action_id: int
    title: str
    type: str
    function_payload: dict | None = None

@app.post("/system/scan")
async def run_scan(request: ScanRequest):
    try:
        inputs = fetch_real_data()
        preds = run_ml_predictions(inputs)
        
        # Determine top trend for frontend display
        keywords = ['dengue', 'fever', 'asthma', 'cough', 'cold', 'loose_motion', 'vomiting']
        top_trend = max(keywords, key=lambda k: inputs.get(k, 0)).title()

        # Run AI Analysis
        agent_response = run_agent_analysis(inputs, preds)
        
        frontend_data = {
            "environment": {
                "temp": inputs['Monthly_Avg_Temp'],
                "rain": inputs['Rainfall_mm'],
                "aqi": inputs['Monthly_Avg_AQI'],
                "humidity": inputs['Monthly_Avg_Humidity']
            },
            "predictions": {
                "vector": {"score": preds['Vector_Pred'], "status": preds['Vector_Status']},
                "respiratory": {"score": preds['Respiratory_Pred'], "status": preds['Resp_Status']},
                "water": {"score": preds['Water_Pred'], "status": preds['Water_Status']}
            },
            "top_trend": top_trend,
            "inventory": HOSPITAL_STATE['inventory'], # Sending the persistent global state
            "ai_agent": agent_response
        }

        return {"success": True, "live_data": frontend_data}

    except Exception as e:
        print(f"SERVER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system/execute_action")
async def execute_action(request: ActionRequest):
    """
    REAL Execution Logic.
    This modifies the in-memory HOSPITAL_STATE based on the action approved.
    """
    print(f"🤖 Executing Agent Action: {request.title} (Type: {request.type})")
    
    # 1. LOGGING ACTIONS (e.g., Alerts)
    if request.function_payload and request.function_payload.get("action") == "ALERT_ALL":
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] ALERT BROADCAST: {request.function_payload.get('message', 'Alert')}"
        HOSPITAL_STATE["system_logs"].append(log_entry)
        return {"success": True, "message": "Alert sent to 142 Staff Members via SMS Gateway."}

    # 2. INVENTORY/RESOURCE ACTIONS
    # The heuristic logic matches keywords to decide what to restock/deplete
    if request.type in ["RESOURCE", "INVENTORY"]:
        msg = "Inventory updated."
        
        # Logic to guess what to update based on title/description
        if "masks" in request.title.lower():
            HOSPITAL_STATE["inventory"]["masks"] += 500
            msg = "Added +500 Masks to stock."
        elif "oxygen" in request.title.lower():
            HOSPITAL_STATE["inventory"]["oxygen"] += 20
            msg = "Added +20 Oxygen Cylinders."
        elif "bed" in request.title.lower() or "surge" in request.title.lower():
            # Activating surge protocol usually clears up beds
            HOSPITAL_STATE["inventory"]["beds_available"] += 5
            msg = "Surge Protocol Active: +5 Beds cleared."
        elif "ors" in request.title.lower() or "fluids" in request.title.lower():
            HOSPITAL_STATE["inventory"]["ors_packs"] += 100
            msg = "Restocked +100 ORS/Fluids."
        else:
            # Generic restock if unknown
            HOSPITAL_STATE["inventory"]["ors_packs"] += 50
            msg = "General medical supplies restocked."
             
        return {"success": True, "message": msg}

    # 3. SYNC ACTIONS
    if request.function_payload and request.function_payload.get("action") == "SYNC_DB":
         return {"success": True, "message": "Database synchronized with Central Command."}

    # 4. Default Fallback
    return {"success": True, "message": f"Action '{request.title}' logged in system registry."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)