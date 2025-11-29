import os
import sys
import json
import warnings
import hashlib
import random
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- EMAIL IMPORTS ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

# Filter warnings for cleaner logs
warnings.filterwarnings("ignore")

load_dotenv()

# --- 1. CONFIGURATION & CREDENTIALS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTIC_DIR = os.path.join(BASE_DIR, "..", 'agentic')
PO_DIR = os.path.join(BASE_DIR, "generated_pos")

# Create PO Directory if not exists
if not os.path.exists(PO_DIR):
    os.makedirs(PO_DIR)

if AGENTIC_DIR not in sys.path:
    sys.path.append(AGENTIC_DIR)

# SMTP CONFIGURATION
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD").replace(" ", "")

# DEMO OVERRIDE: Send all emails here
DEMO_RECIPIENT_EMAIL = os.getenv("DEMO_RECIPIENT_EMAIL")
# --- 2. IMPORT TEAM MODULES ---
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

# --- 3. GLOBAL STATE & CACHE ---
# UPDATED: Realistic Hospital Inventory
HOSPITAL_STATE = {
    "inventory": {
        "N95 Masks": 1240,
        "Oxygen Cylinders (Type D)": 45, 
        "ICU Beds Available": 8, 
        "IV Fluids (RL 500ml)": 120,
        "Dengue IgG Kits": 50,
        "Paracetamol Infusion": 85
    },
    "system_logs": []
}

DATA_CACHE = {
    "weather": {"data": None, "timestamp": None},
    "aqi": {"data": None, "timestamp": None},
    "trends": {"data": None, "timestamp": None},
    "baseline": {"data": None, "timestamp": None}
}

AGENT_CACHE = {
    "last_hash": None,
    "response": None,
    "timestamp": None
}

DATA_TTL = timedelta(minutes=60)
AGENT_TTL = timedelta(minutes=30)

# --- 4. AGENT TOOLS (REAL IMPLEMENTATIONS) ---

def send_email_real(subject, html_body):
    """
    Sends real HTML email via Gmail using SMTP_SSL (Port 465).
    """
    recipient = DEMO_RECIPIENT_EMAIL
    print(f"📧 AGENT: Sending HTML Email to {recipient}...")
    
    if not SMTP_PASSWORD:
        print("   ⚠️ Gmail credentials not set correctly.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"[Pulse Predict] {subject}"
        msg['From'] = SMTP_EMAIL
        msg['To'] = recipient

        part = MIMEText(html_body, "html")
        msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            
        print("   ✅ Email sent successfully.")
        return True
    except Exception as e:
        print(f"   ❌ SMTP Error to {recipient}: {e}")
        return False

def generate_purchase_order_file(po_number, item, quantity, vendor, date_str, total_cost):
    """
    Generates a formal Purchase Order text file.
    """
    filename = f"{po_number}_{item.replace(' ', '_')}.txt"
    filepath = os.path.join(PO_DIR, filename)
    
    content = f"""
    =========================================
             HOSPITAL PURCHASE ORDER
    =========================================
    PO Number: {po_number}
    Date:      {date_str}
    Vendor:    {vendor}
    -----------------------------------------
    ITEM DETAILS:
    
    Item Name:       {item}
    Quantity:        {quantity}
    Total Cost:      ${total_cost:,.2f}
    Priority:        URGENT / AUTOMATED
    -----------------------------------------
    Authorized By:   Pulse Predict AI (Automated Agent)
    Status:          PENDING FULFILLMENT
    =========================================
    """
    
    try:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"   ✅ PO File Generated: {filepath}")
        return True
    except Exception as e:
        print(f"   ❌ PO File Generation Failed: {e}")
        return False

async def delayed_inventory_update(item: str, qty: int):
    """
    Background task to simulate shipping time.
    """
    print(f"🚚 LOGISTICS: Shipping {qty} units of {item}... (10s delay)")
    await asyncio.sleep(10)
    
    # Fuzzy matching for the new realistic inventory keys
    target_key = None
    for key in HOSPITAL_STATE["inventory"].keys():
        # Check if the ordered item string is roughly inside the inventory key
        # e.g., "masks" in "N95 Masks"
        if item.split(" ")[0].lower() in key.lower(): 
            target_key = key
            break
            
    if target_key:
        HOSPITAL_STATE["inventory"][target_key] += qty
        print(f"✅ RESTOCK COMPLETE: {target_key} increased by {qty}. New Total: {HOSPITAL_STATE['inventory'][target_key]}")
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] INVENTORY UPDATE: Received {qty} {target_key}."
        HOSPITAL_STATE["system_logs"].append(log_entry)
    else:
        # If item doesn't exist (e.g., "Mosquito Nets"), add it dynamically
        HOSPITAL_STATE["inventory"][item] = qty
        print(f"✅ NEW ITEM ADDED: {item} initialized with {qty}.")

# --- 5. DATA GATHERING (WITH CACHING) ---

def get_cached_data(key, fetch_function):
    now = datetime.now()
    entry = DATA_CACHE.get(key)
    if entry["data"] and entry["timestamp"] and (now - entry["timestamp"] < DATA_TTL):
        return entry["data"]
    try:
        data = fetch_function()
        if data:
            DATA_CACHE[key] = {"data": data, "timestamp": now}
        return data
    except Exception as e:
        return None

def fetch_real_data():
    weather = get_cached_data("weather", get_current_month_weather)
    aqi = get_cached_data("aqi", get_current_month_aqi)
    trends = get_cached_data("trends", get_current_month_trends)
    baseline = get_cached_data("baseline", get_monthly_baseline)

    # Fallbacks
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
        "Monthly_Avg_Temp": float(weather.get('Monthly_Avg_Temp', 0)),
        "Rainfall_mm": float(weather.get('Rainfall_mm', 0)),
        "Rainfall_Lag_2": float(weather.get('Rainfall_Lag_2', 0)),
        "Monthly_Avg_Humidity": float(weather.get('Monthly_Avg_Humidity', 0)),
        "Monthly_Avg_AQI": float(aqi.get('Monthly_Avg_AQI', 0)),
        "Days_Severe_AQI": float(aqi.get('Days_Severe_AQI', 0)),
        "dengue": int(trends.get('dengue', 0)),
        "fever": int(trends.get('fever', 0)),
        "asthma": int(trends.get('asthma', 0)),
        "cough": int(trends.get('cough', 0)),
        "cold": int(trends.get('cold', 0)),
        "loose_motion": int(trends.get('loose motion', 0)),
        "vomiting": int(trends.get('vomiting', 0)),
        "stomach_pain": int(trends.get('stomach pain', 0)),
    }

# --- 6. PREDICTIONS ---

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

# --- 7. AI AGENT ---

def run_agent_analysis(inputs, predictions):
    if not os.getenv("GROQ_API_KEY"):
        return {"summary": "No API Key.", "actions": []}

    current_state_str = json.dumps({
        "temp": inputs['Monthly_Avg_Temp'],
        "rain": inputs['Rainfall_mm'],
        "aqi": inputs['Monthly_Avg_AQI'],
        "vector_risk": predictions['Vector_Pred'],
        "resp_risk": predictions['Respiratory_Pred'],
        "water_risk": predictions['Water_Pred']
    }, sort_keys=True)
    
    current_hash = hashlib.md5(current_state_str.encode()).hexdigest()
    
    now = datetime.now()
    if (AGENT_CACHE["response"] and 
        AGENT_CACHE["last_hash"] == current_hash and 
        AGENT_CACHE["timestamp"] and 
        (now - AGENT_CACHE["timestamp"] < AGENT_TTL)):
        print("🧠 Agent: Using Cached Strategy.")
        return AGENT_CACHE["response"]

    print("🧠 Agent: Generating New Strategy...")
    
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
        
        trends_list = ['dengue', 'fever', 'asthma', 'cough', 'cold', 'loose_motion', 'vomiting']
        trends_map = {k: inputs.get(k, 0) for k in trends_list}
        sorted_trends = sorted(trends_map.items(), key=lambda item: item[1], reverse=True)
        active_trends = [f"{k.replace('_', ' ').title()} ({v})" for k, v in sorted_trends[:3] if v > 0]
        trends_context = ", ".join(active_trends) if active_trends else "None"

        system_prompt = f"""
        You are Pulse Predict, an automated Hospital Command System.
        
        CONTEXT:
        - Trends: {trends_context}
        - Risks: Vector({predictions['Vector_Status']}), Respiratory({predictions['Resp_Status']}), Water({predictions['Water_Status']})
        - Inventory: {json.dumps(HOSPITAL_STATE['inventory'])}
        
        AVAILABLE TOOLS:
        1. ALERT_EMAIL(recipient: str, subject: str, body: str) -> Use for high risks or surges.
        2. GENERATE_PO(item: str, quantity: int, vendor: str) -> Use if inventory items (Masks, Oxygen, Fluids) seem low relative to risk.
        3. GENERAL_LOG(action: str) -> For internal tracking.

        TASK:
        Generate 3 high-priority Action Items.
        Return ONLY JSON:
        {{
            "summary": "...",
            "actions": [
                {{
                    "id": 1,
                    "title": "Action Title",
                    "type": "COMMUNICATION|INVENTORY|PROTOCOL", 
                    "description": "...",
                    "priority": "High|Medium",
                    "executable": true/false,
                    "status": "PENDING",
                    "function_payload": {{ "tool": "ALERT_EMAIL", "args": {{...}} }} 
                }}
            ]
        }}
        """
        
        response = llm.invoke([SystemMessage(content=system_prompt), ("user", "Generate Action Plan.")])
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_json)
        
        AGENT_CACHE["last_hash"] = current_hash
        AGENT_CACHE["response"] = result
        AGENT_CACHE["timestamp"] = now
        
        return result

    except Exception as e:
        print(f"Agent Error: {e}")
        return {
            "summary": "System running in manual fallback mode.",
            "actions": []
        }

# --- 8. API ENDPOINTS ---

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
        
        keywords = ['dengue', 'fever', 'asthma', 'cough', 'cold', 'loose_motion', 'vomiting']
        top_trend = max(keywords, key=lambda k: inputs.get(k, 0)).title()

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
            "inventory": HOSPITAL_STATE['inventory'], 
            "ai_agent": agent_response
        }

        return {"success": True, "live_data": frontend_data}

    except Exception as e:
        print(f"SERVER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system/execute_action")
async def execute_action(request: ActionRequest, background_tasks: BackgroundTasks):
    print(f"🤖 Executing Agent Action: {request.title}")
    
    # 1. Update Status in Cache
    if AGENT_CACHE["response"] and "actions" in AGENT_CACHE["response"]:
        for action in AGENT_CACHE["response"]["actions"]:
            if action["id"] == request.action_id:
                action["status"] = "EXECUTED"
                break

    payload = request.function_payload or {}
    tool = payload.get("tool")
    args = payload.get("args", {})

    # --- TOOL 1: EMAIL ALERT ---
    if tool == "ALERT_EMAIL":
        subject = args.get("subject", "Automated Alert")
        body_text = args.get("body", "Please check the dashboard.")
        
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #f4f4f4; padding: 20px;">
              <div style="background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #d9534f; border-bottom: 2px solid #d9534f; padding-bottom: 10px;">
                  🚨 Pulse Predict Alert
                </h2>
                <p style="font-size: 16px;"><strong>Subject:</strong> {subject}</p>
                <div style="background-color: #fff3f3; border-left: 4px solid #d9534f; padding: 15px; margin: 15px 0;">
                  {body_text}
                </div>
                <p style="font-size: 12px; color: #777; margin-top: 20px;">
                  Sent automatically by Pulse Predict Agent.<br>
                  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        
        success = send_email_real(subject, html_content)
        if success:
            return {"success": True, "message": f"📧 HTML Alert sent to {DEMO_RECIPIENT_EMAIL}"}
        else:
            return {"success": True, "message": "📧 Email Failed (Check Server Logs)"}

    # --- TOOL 2: PURCHASE ORDER ---
    elif tool == "GENERATE_PO":
        item = args.get("item", "Medical Supplies")
        qty = args.get("quantity", 100)
        vendor = args.get("vendor", "MedCorp Inc.")
        
        # GENERATE COST
        unit_price = random.uniform(10.0, 150.0) # Random price between $10 and $150
        total_cost = unit_price * qty
        
        po_num = f"PO-{random.randint(10000, 99999)}"
        date_str = datetime.now().strftime("%Y-%m-%d")

        # A. Generate Text File
        generate_purchase_order_file(po_number=po_num, item=item, quantity=qty, vendor=vendor, date_str=date_str, total_cost=total_cost)
        
        # B. Send Invoice Email
        html_invoice = f"""
        <html>
          <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #555;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0, 0, 0, .15);">
                <table cellpadding="0" cellspacing="0" style="width: 100%; line-height: inherit; text-align: left;">
                    <tr class="top">
                        <td colspan="2" style="padding-bottom: 20px;">
                            <table style="width: 100%;">
                                <tr>
                                    <td style="font-size: 45px; line-height: 45px; color: #333;">
                                        🏥
                                    </td>
                                    <td style="text-align: right; padding-bottom: 20px;">
                                        Invoice #: {po_num}<br>
                                        Created: {date_str}<br>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr class="heading">
                        <td style="background: #eee; border-bottom: 1px solid #ddd; font-weight: bold; padding: 10px;">Item</td>
                        <td style="background: #eee; border-bottom: 1px solid #ddd; font-weight: bold; padding: 10px; text-align: right;">Quantity</td>
                    </tr>
                    <tr class="item">
                        <td style="border-bottom: 1px solid #eee; padding: 10px;">{item}</td>
                        <td style="border-bottom: 1px solid #eee; padding: 10px; text-align: right;">{qty}</td>
                    </tr>
                    <tr class="total">
                        <td colspan="2" style="border-top: 2px solid #eee; font-weight: bold; text-align: right; padding: 10px;">
                           Total Cost: ${total_cost:,.2f}
                        </td>
                    </tr>
                </table>
                <p style="text-align: center; font-size: 12px; margin-top: 30px;">
                    Authorized by Pulse Predict AI Agent.
                </p>
            </div>
          </body>
        </html>
        """
        send_email_real(f"Invoice {po_num}", html_invoice)

        # C. Schedule Inventory Update
        background_tasks.add_task(delayed_inventory_update, item, qty)
        
        return {"success": True, "message": f"📝 PO #{po_num} Emailed (${total_cost:,.2f}). Stock updates in 10s."}

    # 4. Fallback Logic
    return {"success": True, "message": f"Action '{request.title}' logged in system registry."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)