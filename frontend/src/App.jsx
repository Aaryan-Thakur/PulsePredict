import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Wind, 
  Droplets, 
  Thermometer, 
  CheckCircle, 
  Shield, 
  Zap, 
  Loader,
  TrendingUp,
  Hospital,
  ClipboardList,
  RefreshCw,
  UserCog,
  Server,
  AlertTriangle 
} from 'lucide-react';

// --- MOCK DATA FOR DEMO MODE ---
const MOCK_DATA = {
  environment: {
    temp: 32.5,
    rain: 120.5,
    aqi: 165.0,
    humidity: 78.0
  },
  predictions: {
    vector: { score: 8.5, status: "🔴 CRITICAL" },
    respiratory: { score: 2.1, status: "🟢 NORMAL" },
    water: { score: 4.5, status: "🟠 WARNING" }
  },
  top_trend: "Dengue",
  inventory: {
    masks: 454,
    oxygen: 32,
    beds_available: 2,
    ors_packs: 45
  },
  ai_agent: {
    summary: "Critical vector-borne disease risk detected. High humidity and temperature creating ideal breeding grounds. Immediate automated intervention recommended.",
    actions: [
      { 
        id: 1, 
        title: "Broadcast Dengue Alert", 
        type: "COMMUNICATION", 
        description: "Send SMS blast to all on-call staff regarding triage protocols.", 
        priority: "High",
        executable: true,
        function_payload: { action: "ALERT_ALL", message: "High Dengue Risk" }
      },
      { 
        id: 2, 
        title: "Update Inventory Logs", 
        type: "INVENTORY", 
        description: "Sync current stock levels with central supply database.", 
        priority: "Medium",
        executable: true,
        function_payload: { action: "SYNC_DB" }
      },
      { 
        id: 3, 
        title: "Sanitize Ward C", 
        type: "PROTOCOL", 
        description: "Physical deep cleaning required for Ward C.", 
        priority: "High",
        executable: false, // Manual task
        function_payload: null
      }
    ]
  }
};

// --- COMPONENTS ---

const MetricCard = ({ icon: Icon, label, value, unit, color = "text-blue-400" }) => (
  <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 flex items-center space-x-4 shadow-lg hover:border-blue-500/30 transition-colors">
    <div className={`p-3 rounded-lg bg-slate-700/50 ${color}`}>
      <Icon size={24} />
    </div>
    <div>
      <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider">{label}</p>
      <div className="flex items-baseline space-x-1">
        <span className="text-2xl font-bold text-white">{value}</span>
        <span className="text-sm text-slate-500">{unit}</span>
      </div>
    </div>
  </div>
);

const RiskCard = ({ title, score, status, type }) => {
  let statusColor = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  let barColor = "bg-emerald-500";
  
  if (status.includes("WARNING")) {
    statusColor = "bg-amber-500/10 text-amber-400 border-amber-500/20";
    barColor = "bg-amber-500";
  } else if (status.includes("CRITICAL") || status.includes("SURGE")) {
    statusColor = "bg-rose-500/10 text-rose-400 border-rose-500/20";
    barColor = "bg-rose-500";
  }

  const Icons = {
    vector: Zap,
    respiratory: Wind,
    water: Droplets
  };
  const Icon = Icons[type] || Activity;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg relative overflow-hidden group">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${statusColor}`}>
            <Icon size={20} />
          </div>
          <h3 className="font-semibold text-slate-200">{title}</h3>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-bold border ${statusColor}`}>
          {status}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Risk Index</span>
          <span className="text-white font-mono">{score} / 10.0</span>
        </div>
        <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden">
          <div 
            className={`h-full ${barColor} transition-all duration-1000 ease-out`} 
            style={{ width: `${(score / 10) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

const ActionCard = ({ action, onExecute, isExecuting, isExecuted }) => {
  if (isExecuted) {
    return (
      <div className="bg-emerald-900/20 border border-emerald-500/30 p-4 rounded-lg flex items-center justify-between mb-3 animate-in fade-in slide-in-from-bottom-2">
        <div className="flex items-center space-x-3 text-emerald-400">
          <CheckCircle size={20} />
          <span className="font-medium line-through decoration-emerald-500/50 text-slate-400">{action.title}</span>
        </div>
        <span className="text-xs text-emerald-500 font-mono">EXECUTED</span>
      </div>
    );
  }

  // Determine if this is a "Human" task or an "Agent" task
  const isExecutable = action.executable;

  return (
    <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-lg mb-3 hover:border-blue-500/50 transition-colors">
      <div className="flex justify-between items-start">
        <div className="flex-1 pr-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className={`text-xs px-2 py-0.5 rounded border ${
              action.priority === 'High' 
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }`}>
              {action.priority}
            </span>
            <span className="text-xs text-slate-500 bg-slate-700/50 px-2 py-0.5 rounded uppercase font-mono">
              {action.type}
            </span>
          </div>
          <h4 className="font-bold text-slate-200">{action.title}</h4>
          <p className="text-sm text-slate-400 mt-1 leading-snug">{action.description}</p>
        </div>
        
        {isExecutable ? (
          <button
            onClick={() => onExecute(action)}
            disabled={isExecuting}
            className="flex-shrink-0 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-900/20 border border-blue-500"
          >
            {isExecuting ? <Loader className="animate-spin mr-2" size={14} /> : <Zap size={14} className="mr-2" />}
            {isExecuting ? "Working..." : "AUTO-RUN"}
          </button>
        ) : (
          <div className="flex-shrink-0 flex items-center text-slate-500 bg-slate-800 px-3 py-2 rounded-lg border border-slate-700 cursor-not-allowed opacity-75" title="Requires Human Intervention">
             <UserCog size={16} className="mr-2" />
             <span className="text-xs font-mono">MANUAL TASK</span>
          </div>
        )}
      </div>
    </div>
  );
};

// --- MAIN APP ---

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [executingId, setExecutingId] = useState(null);
  const [executedActions, setExecutedActions] = useState(new Set());
  const [statusMsg, setStatusMsg] = useState("");
  const [isDemoMode, setIsDemoMode] = useState(false);

  const fetchData = async () => {
    setLoading(true); // Ensure loading state is reset on retry
    try {
      // 1. Attempt Fetch System State
      const response = await fetch('http://localhost:8000/system/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: "initial_scan" })
      });
      
      if (!response.ok) throw new Error("Backend not available");
      
      const result = await response.json();
      if (result.success) {
        setData(result.live_data);
        setIsDemoMode(false);
      }
    } catch (error) {
      console.warn("Backend unavailable. Switching to DEMO MODE automatically.");
      // FALLBACK TO MOCK DATA AUTOMATICALLY
      setData(MOCK_DATA);
      setIsDemoMode(true);
      setStatusMsg("Demo Mode Active: Backend unreachable");
      setTimeout(() => setStatusMsg(""), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteAction = async (action) => {
    setExecutingId(action.id);
    setStatusMsg(`Agent executing: ${action.title}...`);
    
    try {
      // 2. Execute Real Action
      const response = await fetch('http://localhost:8000/system/execute_action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          action_id: action.id, 
          title: action.title,
          type: action.type,
          function_payload: action.function_payload 
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setExecutedActions(prev => new Set([...prev, action.id]));
        
        // 3. Refresh Data to show Real State Change
        setTimeout(() => {
           fetchData(); 
           setStatusMsg(`Success: ${result.message}`);
           setTimeout(() => setStatusMsg(""), 3000);
        }, 1000);
      }
    } catch (error) {
      console.warn("Execution failed (Demo Mode): Simulating success");
      // SIMULATE SUCCESS IN DEMO MODE
      setTimeout(() => {
        setExecutedActions(prev => new Set([...prev, action.id]));
        setStatusMsg("Success: Action logged (Demo Mode)");
        setExecutingId(null);
        setTimeout(() => setStatusMsg(""), 3000);
      }, 1500);
    } finally {
      // If fetch succeeds, we might need to clear executingId here if not handled in try
      if (!isDemoMode) setExecutingId(null); 
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-blue-400">
        <Loader className="animate-spin mb-4" size={48} />
        <p className="font-mono text-sm tracking-widest animate-pulse">CONNECTING TO SENTIN-AI CORE...</p>
      </div>
    );
  }

  if (!data) {
    // This fallback screen is less likely to appear now, but kept for safety
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-rose-500">
        <AlertTriangle size={48} className="mb-4" />
        <h2 className="font-mono text-xl font-bold">SYSTEM ERROR</h2>
        <p className="text-slate-500 text-sm mt-2 mb-6 max-w-md text-center">
          Unable to load system data.
        </p>
        <button onClick={fetchData} className="px-4 py-2 bg-slate-800 rounded hover:bg-slate-700 text-white border border-slate-700 transition-colors">
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      
      {/* STATUS TOAST */}
      {statusMsg && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-800 border border-blue-500/50 text-blue-200 px-4 py-3 rounded-lg shadow-2xl flex items-center animate-in slide-in-from-bottom-5">
          <Server size={16} className="mr-3" />
          <span className="text-sm font-mono">{statusMsg}</span>
        </div>
      )}

      {/* HEADER */}
      <header className="bg-slate-900/50 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="bg-blue-600 p-2 rounded-lg shadow-lg shadow-blue-500/20">
              <Shield className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Pulse Predict</h1>
              <p className="text-xs text-blue-400 font-mono tracking-wider">AI-ENHANCED HOSPITAL SENTINEL</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
             {isDemoMode ? (
               <div className="hidden md:flex items-center space-x-2 text-xs font-mono text-amber-500 bg-amber-900/20 px-3 py-1.5 rounded-full border border-amber-500/30">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                  <span>DEMO MODE</span>
               </div>
             ) : (
               <div className="hidden md:flex items-center space-x-2 text-xs font-mono text-slate-500 bg-slate-900 px-3 py-1.5 rounded-full border border-slate-800">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>SYSTEM ONLINE</span>
               </div>
             )}
             
             <button 
               onClick={fetchData}
               className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white"
               title="Refresh Data"
             >
               <RefreshCw size={20} />
             </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        
        {/* TOP METRICS ROW */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard 
            icon={Thermometer} 
            label="Avg Temp" 
            value={data.environment.temp} 
            unit="°C" 
            color="text-orange-400"
          />
          <MetricCard 
            icon={Droplets} 
            label="Rainfall" 
            value={data.environment.rain} 
            unit="mm" 
            color="text-blue-400"
          />
          <MetricCard 
            icon={Wind} 
            label="Air Quality" 
            value={data.environment.aqi} 
            unit="AQI" 
            color={data.environment.aqi > 150 ? "text-rose-400" : "text-emerald-400"}
          />
          <MetricCard 
            icon={TrendingUp} 
            label="Top Symptom" 
            value={data.top_trend} 
            unit="" 
            color="text-purple-400"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* LEFT COLUMN: RISK MODELS (Width 5/12) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-bold text-white flex items-center">
                <Activity className="mr-2 text-blue-500" size={20} />
                Real-Time Risk Models
              </h2>
            </div>
            
            <div className="space-y-4">
              <RiskCard 
                title="Vector-Borne (Dengue/Malaria)" 
                type="vector"
                score={data.predictions.vector.score} 
                status={data.predictions.vector.status} 
              />
              <RiskCard 
                title="Respiratory (Flu/Asthma)" 
                type="respiratory"
                score={data.predictions.respiratory.score} 
                status={data.predictions.respiratory.status} 
              />
              <RiskCard 
                title="Water-Borne (Cholera/Typhoid)" 
                type="water"
                score={data.predictions.water.score} 
                status={data.predictions.water.status} 
              />
            </div>

            {/* Inventory Snapshot Mini-Widget */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mt-6">
              <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-4">Live Inventory Status</h3>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(data.inventory).map(([key, val]) => (
                  <div key={key} className="flex justify-between items-center p-2 bg-slate-800 rounded hover:bg-slate-700 transition-colors">
                    <span className="text-xs text-slate-400 capitalize">{key.replace('_', ' ')}</span>
                    <span className={`text-sm font-mono font-bold ${val < 10 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {val}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: AI COMMAND CENTER (Width 7/12) */}
          <div className="lg:col-span-7">
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
              
              {/* Terminal Header */}
              <div className="bg-slate-950 px-5 py-3 border-b border-slate-800 flex justify-between items-center">
                <div className="flex items-center space-x-2">
                   <div className="w-3 h-3 rounded-full bg-rose-500"></div>
                   <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                   <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                </div>
                <div className="text-xs font-mono text-slate-500">sentin_ai_agent.exe</div>
              </div>

              <div className="p-6">
                
                {/* 1. Strategic Summary Section */}
                <div className="mb-8">
                  <h3 className="text-blue-400 font-mono text-sm mb-3 flex items-center">
                    <Hospital className="mr-2" size={16} /> 
                    STRATEGIC ANALYSIS
                  </h3>
                  <div className="p-4 bg-slate-800/50 border-l-2 border-blue-500 rounded-r-lg">
                    <p className="text-slate-300 leading-relaxed text-sm">
                      {data.ai_agent?.summary || "System analyzing data patterns..."}
                    </p>
                  </div>
                </div>

                {/* 2. Action Items Feed */}
                <div>
                  <h3 className="text-blue-400 font-mono text-sm mb-4 flex items-center">
                    <ClipboardList className="mr-2" size={16} /> 
                    RECOMMENDED ACTIONS
                  </h3>
                  
                  <div className="space-y-1">
                    {data.ai_agent?.actions?.map((action) => (
                      <ActionCard 
                        key={action.id} 
                        action={action}
                        isExecuting={executingId === action.id}
                        isExecuted={executedActions.has(action.id)}
                        onExecute={handleExecuteAction}
                      />
                    ))}
                    
                    {!data.ai_agent?.actions && (
                      <div className="text-center py-10 text-slate-600 italic">
                        No immediate actions required.
                      </div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}