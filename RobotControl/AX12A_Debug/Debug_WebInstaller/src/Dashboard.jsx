import React, { useState, useEffect } from 'react';
import { serialService } from './SerialService';
import { Link, Zap, Thermometer, Activity, RefreshCw, Settings, Search, Move, Database } from 'lucide-react';

function Dashboard() {
  const [connected, setConnected] = useState(false);
  const [servos, setServos] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [status, setStatus] = useState(null);
  const [memory, setMemory] = useState(null); // { eeprom: [], ram: [] }
  const [goalPos, setGoalPos] = useState(512);
  const [goalSpeed, setGoalSpeed] = useState(100);

  useEffect(() => {
    serialService.onDisconnect = () => setConnected(false);
    
    serialService.onMessage = (data) => {
      if (data.type === 'scan') {
        setServos(data.found);
        if (data.found.length > 0 && activeId === null) {
          setActiveId(data.found[0]);
        }
      } else if (data.type === 'status') {
        setStatus(data);
      } else if (data.type === 'dump') {
        setMemory(data);
      }
    };

    return () => {
      serialService.onMessage = null;
    };
  }, [activeId]);

  // Polling for status
  useEffect(() => {
    let interval;
    if (connected && activeId !== null) {
      interval = setInterval(() => {
        serialService.sendCommand(`jstatus ${activeId}`);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [connected, activeId]);

  const handleConnect = async () => {
    if (connected) {
      await serialService.disconnect();
    } else {
      const success = await serialService.connect();
      if (success) {
        setConnected(true);
        handleScan();
      }
    }
  };

  const handleScan = () => {
    serialService.sendCommand('jscan');
  };

  const handleMove = () => {
    if (activeId !== null) {
      serialService.sendCommand(`move ${activeId} ${goalPos} ${goalSpeed}`);
    }
  };

  const handleReadMemory = () => {
    if (activeId !== null) {
      serialService.sendCommand(`dump ${activeId}`);
    }
  };

  const handleFactoryReset = () => {
    if (activeId !== null) {
        if(window.confirm(`Are you sure you want to factory reset servo ID ${activeId}? This changes ID to 1 and Baud to 1000000.`)) {
            serialService.sendCommand(`reset ${activeId}`);
        }
    }
  };

  return (
    <div className="dashboard-grid">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="glass-panel">
          <h3>Connection</h3>
          <div style={{ marginBottom: '1rem' }}>
            <span className={`status-badge ${connected ? 'connected' : 'disconnected'}`}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor' }} />
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <button 
            className={`btn ${connected ? 'btn-danger' : 'btn-primary'}`} 
            style={{ width: '100%' }}
            onClick={handleConnect}
          >
            <Link size={18} /> {connected ? 'Disconnect' : 'Connect via USB'}
          </button>
        </div>

        <div className="glass-panel" style={{ opacity: connected ? 1 : 0.5, pointerEvents: connected ? 'auto' : 'none' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Servos</h3>
            <button className="btn btn-primary" onClick={handleScan} style={{ padding: '0.4rem 0.8rem' }} title="Scan for Servos">
              <Search size={16} />
            </button>
          </div>
          
          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>Active Servo ID</label>
            <select 
              value={activeId || ''} 
              onChange={(e) => setActiveId(parseInt(e.target.value))}
              style={{ width: '100%', background: 'rgba(0,0,0,0.3)', color: 'white', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--panel-border)' }}
            >
              <option value="" disabled>Select a servo</option>
              {servos.map(id => <option key={id} value={id}>ID: {id}</option>)}
            </select>
          </div>
        </div>

        <div className="glass-panel" style={{ opacity: connected ? 1 : 0.5, pointerEvents: connected ? 'auto' : 'none' }}>
          <h3>Control</h3>
          <div className="form-group">
            <label>Goal Position ({goalPos})</label>
            <input 
              type="range" min="0" max="1023" value={goalPos} 
              onChange={(e) => {
                  setGoalPos(e.target.value);
                  if (activeId !== null) serialService.sendCommand(`move ${activeId} ${e.target.value} ${goalSpeed}`);
              }} 
            />
          </div>
          <div className="form-group">
            <label>Moving Speed ({goalSpeed})</label>
            <input 
              type="range" min="0" max="1023" value={goalSpeed} 
              onChange={(e) => setGoalSpeed(e.target.value)} 
            />
          </div>
          <button className="btn btn-accent" style={{ width: '100%', marginTop: '1rem' }} onClick={handleMove}>
            <Move size={18} /> Send Move
          </button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content" style={{ opacity: connected ? 1 : 0.5, pointerEvents: connected ? 'auto' : 'none' }}>
        
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2><Activity size={24} style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: 'var(--primary)' }} /> Live Status</h2>
          </div>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="label"><Zap size={14} style={{verticalAlign: 'middle'}}/> Voltage</div>
              <div className="value">{status ? status.voltage.toFixed(1) : '--'} V</div>
            </div>
            <div className="metric-card">
              <div className="label"><Thermometer size={14} style={{verticalAlign: 'middle'}}/> Temp</div>
              <div className="value">{status ? status.temp : '--'} °C</div>
            </div>
            <div className="metric-card">
              <div className="label">Load</div>
              <div className="value">{status ? status.load : '--'}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{status ? status.load_dir : ''}</div>
            </div>
            <div className="metric-card">
              <div className="label">Position</div>
              <div className="value">{status ? status.pos : '--'}</div>
            </div>
          </div>
        </div>

        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2><Database size={24} style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: 'var(--accent)' }} /> Control Table (Memory)</h2>
            <div>
              <button className="btn btn-primary" onClick={handleReadMemory} style={{ marginRight: '10px' }}>
                <RefreshCw size={18} /> Read Memory
              </button>
              <button className="btn btn-danger" onClick={handleFactoryReset}>
                 Factory Reset
              </button>
            </div>
          </div>

          {!memory ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Click 'Read Memory' to fetch the full EEPROM and RAM tables.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="data-table-wrapper">
                <table style={{ fontSize: '0.85rem' }}>
                  <thead>
                    <tr><th colSpan="3" style={{ textAlign: 'center', background: 'rgba(139, 92, 246, 0.2)' }}>EEPROM (Non-Volatile)</th></tr>
                    <tr><th>Addr</th><th>Name</th><th>Value</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>3</td><td>ID</td><td>{memory.eeprom[3]}</td></tr>
                    <tr><td>4</td><td>Baud Rate</td><td>{memory.eeprom[4]}</td></tr>
                    <tr><td>5</td><td>Return Delay Time</td><td>{memory.eeprom[5]}</td></tr>
                    <tr><td>6</td><td>CW Angle Limit</td><td>{memory.eeprom[6] | (memory.eeprom[7] << 8)}</td></tr>
                    <tr><td>8</td><td>CCW Angle Limit</td><td>{memory.eeprom[8] | (memory.eeprom[9] << 8)}</td></tr>
                    <tr><td>11</td><td>High Limit Temp</td><td>{memory.eeprom[11]} °C</td></tr>
                    <tr><td>12</td><td>Low Limit Voltage</td><td>{(memory.eeprom[12] / 10).toFixed(1)} V</td></tr>
                    <tr><td>13</td><td>High Limit Voltage</td><td>{(memory.eeprom[13] / 10).toFixed(1)} V</td></tr>
                    <tr><td>14</td><td>Max Torque</td><td>{memory.eeprom[14] | (memory.eeprom[15] << 8)}</td></tr>
                    <tr><td>16</td><td>Status Return Lvl</td><td>{memory.eeprom[16]}</td></tr>
                  </tbody>
                </table>
              </div>

              <div className="data-table-wrapper">
                <table style={{ fontSize: '0.85rem' }}>
                  <thead>
                    <tr><th colSpan="3" style={{ textAlign: 'center', background: 'rgba(59, 130, 246, 0.2)' }}>RAM (Volatile)</th></tr>
                    <tr><th>Addr</th><th>Name</th><th>Value</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>24</td><td>Torque Enable</td><td>{memory.ram[24 - 24]}</td></tr>
                    <tr><td>25</td><td>LED</td><td>{memory.ram[25 - 24]}</td></tr>
                    <tr><td>26</td><td>CW Compl Margin</td><td>{memory.ram[26 - 24]}</td></tr>
                    <tr><td>27</td><td>CCW Compl Margin</td><td>{memory.ram[27 - 24]}</td></tr>
                    <tr><td>28</td><td>CW Compl Slope</td><td>{memory.ram[28 - 24]}</td></tr>
                    <tr><td>29</td><td>CCW Compl Slope</td><td>{memory.ram[29 - 24]}</td></tr>
                    <tr><td>30</td><td>Goal Position</td><td>{memory.ram[30 - 24] | (memory.ram[31 - 24] << 8)}</td></tr>
                    <tr><td>32</td><td>Moving Speed</td><td>{memory.ram[32 - 24] | (memory.ram[33 - 24] << 8)}</td></tr>
                    <tr><td>34</td><td>Torque Limit</td><td>{memory.ram[34 - 24] | (memory.ram[35 - 24] << 8)}</td></tr>
                    <tr><td>36</td><td>Present Position</td><td>{memory.ram[36 - 24] | (memory.ram[37 - 24] << 8)}</td></tr>
                    <tr><td>38</td><td>Present Speed</td><td>{memory.ram[38 - 24] | (memory.ram[39 - 24] << 8)}</td></tr>
                    <tr><td>40</td><td>Present Load</td><td>{memory.ram[40 - 24] | (memory.ram[41 - 24] << 8)}</td></tr>
                    <tr><td>42</td><td>Present Voltage</td><td>{(memory.ram[42 - 24] / 10).toFixed(1)} V</td></tr>
                    <tr><td>43</td><td>Present Temp</td><td>{memory.ram[43 - 24]} °C</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export default Dashboard;
