import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { ActivitySquare, Database, Server, RefreshCw, Cpu, ShieldAlert, Bug, Play, SquareTerminal, Terminal } from 'lucide-react'
import './App.css'

const API_BASE = 'http://localhost:8000'
const WS_BASE = 'ws://localhost:8000/ws'

const PIPELINES_MAP = {
  'sales_etl': { name: 'Sales ETL', icon: <Database size={18} color="#60a5fa" /> },
  'inventory_dbt': { name: 'Inventory DBT', icon: <RefreshCw size={18} color="#34d399" /> },
  'finance_load': { name: 'Finance API', icon: <Server size={18} color="#f59e0b" /> },
  'marketing_sync': { name: 'Marketing Sync', icon: <Database size={18} color="#8b5cf6" /> },
  'hr_data_ingest': { name: 'HR Data Ingest', icon: <Server size={18} color="#ec4899" /> }
}

const ERROR_TEMPLATES = [
  "KeyError: '{col}' not found in source dataset",
  "SchemaMismatch: Expected INT for '{col}' but got VARCHAR",
  "DataQualityError: Column '{col}' contains >50% null values",
  "FormatError: Invalid date format in '{col}'",
  "TimeoutError: Upstream connection timed out after 30s",
  "ConnectionRefused: Failed to connect to port 5432",
  "DeadlockDetected: Transaction aborted on table '{table}'",
  "ValueError: Invalid malformed payload from API"
];
const COLUMNS = ['region_id', 'user_id', 'transaction_amount', 'stock_level', 'created_at', 'session_id'];
const TABLES = ['users', 'transactions', 'inventory', 'events'];

const generateDynamicFailure = () => {
  const pipelines = Object.keys(PIPELINES_MAP);
  const pipeline = pipelines[Math.floor(Math.random() * pipelines.length)];
  const template = ERROR_TEMPLATES[Math.floor(Math.random() * ERROR_TEMPLATES.length)];

  // Fill templates randomly
  let errorMsg = template
    .replace('{col}', COLUMNS[Math.floor(Math.random() * COLUMNS.length)])
    .replace('{table}', TABLES[Math.floor(Math.random() * TABLES.length)]);

  return {
    pipeline: pipeline,
    status: 'failed',
    rows_loaded: Math.floor(Math.random() * 200), // Randomly low rows
    error: errorMsg,
    run_time: new Date().toISOString()
  };
};

function App() {
  const [logs, setLogs] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [dbStatus, setDbStatus] = useState([])
  const [history, setHistory] = useState([])
  const [autoMode, setAutoMode] = useState(false)
  const logsEndRef = useRef(null)

  const fetchState = async () => {
    try {
      const [pipeRes, histRes] = await Promise.all([
        axios.get(`${API_BASE}/pipelines`),
        axios.get(`${API_BASE}/history`)
      ])
      setDbStatus(pipeRes.data)
      setHistory(histRes.data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    // Initial fetch and poll every 3 seconds to sync with DB
    fetchState()
    const intv = setInterval(fetchState, 3000)
    return () => clearInterval(intv)
  }, [])

  useEffect(() => {
    let autoIntv;
    if (autoMode) {
      autoIntv = setInterval(() => {
        handleInjectFailure()
      }, 15000)
    }
    return () => clearInterval(autoIntv)
  }, [autoMode])

  useEffect(() => {
    const ws = new WebSocket(WS_BASE)
    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)
    ws.onerror = () => setIsConnected(false)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setLogs(prev => [...prev, {
        id: Date.now() + Math.random(),
        time: new Date().toLocaleTimeString(),
        sender: data.sender || data.type,
        message: data.message
      }].slice(-100)) // keep last 100 logs
    }
    return () => ws.close()
  }, [])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handleInjectFailure = async () => {
    const dynamicFail = generateDynamicFailure()
    try {
      await axios.post(`${API_BASE}/add-log`, dynamicFail)
    } catch (e) { }
  }

  const getTimelineClass = (stage, currentStatus) => {
    if (currentStatus === 'resolved') return 'completed'
    if (currentStatus === 'failed') {
      if (stage === 'Detecting') return 'failed'
      if (stage === 'Diagnosing') return 'active' // simplifying logic
      return ''
    }
    return 'completed'
  }

  // Determine latest debug info
  const latestHist = history.length > 0 ? history[0] : null;

  return (
    <div className="dashboard-container">
      <header className="header">
        <div className="header-blur">
          <div className="header-title-container">
            <h1><ShieldAlert size={32} color="#8b5cf6" /> PipelineGuard AI</h1>
            <div className="header-subtitle">
              <span>Continuous Real-Time System Monitor</span>
              <div className="status-indicator">
                <span className={`pulse ${isConnected ? '' : 'disconnected'}`} />
                <span>{isConnected ? 'Active Polling' : 'Offline'}</span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              className={`btn-simulate ${autoMode ? 'active' : ''}`}
              onClick={() => setAutoMode(!autoMode)}
            >
              {autoMode ? <SquareTerminal size={20} /> : <Play size={20} />}
              {autoMode ? 'Auto-Test Mode ON' : 'Start Auto-Test'}
            </button>
            <button className="btn-inject" onClick={handleInjectFailure} disabled={!isConnected}>
              <Bug size={18} /> Inject Failure
            </button>
          </div>
        </div>
      </header>

      <div className="grid">
        {Object.entries(PIPELINES_MAP).map(([id, meta]) => {
          const state = dbStatus.find(s => s.pipeline_id === id) || { status: 'ok', error: null, ai_output: null, final_action: null }
          let aiOutput = {}
          if (state.ai_output) {
            try { aiOutput = JSON.parse(state.ai_output) } catch (e) { }
          }

          return (
            <div className="card" key={id}>
              <div className="card-header">
                <div className="card-title-wrap">
                  <div className="icon-box">{meta.icon}</div>
                  {meta.name}
                </div>
                <span className={`status-badge status-${state.status}`}>
                  {state.status === 'ok' ? 'Healthy' : state.status}
                </span>
              </div>

              {state.status !== 'ok' && (
                <div className="timeline">
                  <div className={`timeline-step ${getTimelineClass('Detecting', state.status)}`}><div className="dot"></div><span>Failed</span></div>
                  <div className={`timeline-step ${state.ai_output ? 'completed' : 'active'}`}><div className="dot"></div><span>Diagnosed</span></div>
                  <div className={`timeline-step ${state.status === 'resolved' ? 'completed' : ''}`}><div className="dot"></div><span>Fixed</span></div>
                </div>
              )}

              {state.status === 'failed' && !aiOutput.root_cause && (
                <div className="why-failed">
                  <strong>Trigger Error:</strong><br />{state.error}
                </div>
              )}

              {aiOutput.root_cause && state.status === 'failed' && (
                <div className="why-failed" style={{ borderColor: '#8b5cf6', color: '#a78bfa', background: 'rgba(139,92,246,0.1)' }}>
                  <strong>AI Diagnosis ({aiOutput.cause_type}):</strong><br />{aiOutput.root_cause}
                </div>
              )}

              {state.status === 'resolved' && (
                <div className="why-resolved">
                  <strong>Repaired ({aiOutput.cause_type || 'Unknown'}):</strong><br />{state.final_action}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="main-layout">
        <div className="logs-panel">
          <div className="logs-header">
            <ActivitySquare size={20} color="#8b5cf6" /> Real-time Streaming AI Logs
          </div>
          <div className="logs-content">
            {logs.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.3)', textAlign: 'center', marginTop: '4rem' }}>
                <Cpu size={48} opacity={0.5} style={{ margin: '0 auto 1rem' }} display="block" />
                No logs generated yet. Click "Inject Failure" or "Start Auto-Test".
              </div>
            ) : (
              logs.map(log => (
                <div key={log.id} className="log-entry">
                  <span className="log-time">[{log.time}]</span>
                  <span className={`log-sender sender-${log.sender.toLowerCase().replace('_', '')}`}>[{log.sender}]</span>
                  <span className="log-msg">{log.message}</span>
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>

        <div className="debug-panel">
          <div className="card" style={{ height: '100%', flex: 1 }}>
            <div className="card-header" style={{ marginBottom: '1rem' }}>
              <div className="card-title-wrap"><Terminal size={18} color="#3b82f6" /> AI Debug Core</div>
            </div>

            {latestHist ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>LATEST RAW INPUT ({latestHist.pipeline_id})</span>
                  <div className="code-block">{latestHist.raw_json ? JSON.stringify(JSON.parse(latestHist.raw_json), null, 2) : 'No raw context available'}</div>
                </div>

                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>GEMINI AI OUTPUT</span>
                  <div className="code-block yellow">{latestHist.ai_output ? JSON.stringify(JSON.parse(latestHist.ai_output), null, 2) : 'Reasoning pending...'}</div>
                </div>

                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>MITIGATION ACTION</span>
                  <div className="code-block green">{latestHist.final_action || 'Pending action...'}</div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No history recorded yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
