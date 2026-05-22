import React, { useState } from 'react';
import Installer from './Installer';
import Dashboard from './Dashboard';
import { Settings, Cpu } from 'lucide-react';

function App() {
  const [view, setView] = useState('installer'); // 'installer' or 'dashboard'

  return (
    <div className="app-container">
      <div className="top-bar glass-panel" style={{ padding: '1rem 1.5rem', marginBottom: '2rem' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Cpu className="text-primary" /> AX-12A Studio
        </h2>
        <div>
          <button 
            className={`btn ${view === 'installer' ? 'btn-primary' : ''}`}
            onClick={() => setView('installer')}
            style={{ marginRight: '10px' }}
          >
            Flasher
          </button>
          <button 
            className={`btn ${view === 'dashboard' ? 'btn-primary' : ''}`}
            onClick={() => setView('dashboard')}
          >
            Dashboard
          </button>
        </div>
      </div>

      {view === 'installer' ? <Installer /> : <Dashboard />}
    </div>
  );
}

export default App;
