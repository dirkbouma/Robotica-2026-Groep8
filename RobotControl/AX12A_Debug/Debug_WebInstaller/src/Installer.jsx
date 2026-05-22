import React, { useEffect } from 'react';
import { DownloadCloud, Info } from 'lucide-react';

function Installer() {
  useEffect(() => {
    // Dynamically load the esp-web-tools script if not present
    if (!document.getElementById('esp-web-tools-script')) {
      const script = document.createElement('script');
      script.id = 'esp-web-tools-script';
      script.type = 'module';
      script.src = 'https://unpkg.com/esp-web-tools@10/dist/web/install-button.js?module';
      document.body.appendChild(script);
    }
  }, []);

  return (
    <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
      <div style={{ display: 'inline-flex', background: 'rgba(59, 130, 246, 0.2)', padding: '1.5rem', borderRadius: '50%', marginBottom: '2rem' }}>
        <DownloadCloud size={64} color="var(--primary)" />
      </div>
      <h1>Firmware Installer</h1>
      <p style={{ maxWidth: '600px', margin: '0 auto 2rem auto' }}>
        Connect your ESP32 via USB and click the button below to flash the latest AX-12A Debugger firmware. Ensure your browser supports Web Serial (Chrome, Edge, Opera).
      </p>

      {/* The web component provided by esp-web-tools */}
      <esp-web-install-button manifest="firmware/manifest.json">
        <button slot="activate" className="btn btn-primary" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}>
          Connect & Install
        </button>
        <span slot="unsupported">
          <div style={{ color: 'var(--danger)', marginTop: '1rem' }}>
            Your browser does not support Web Serial. Please use Google Chrome or Microsoft Edge.
          </div>
        </span>
        <span slot="not-allowed">
          <div style={{ color: 'var(--warning)', marginTop: '1rem' }}>
            You must grant access to the serial port.
          </div>
        </span>
      </esp-web-install-button>

      <div style={{ marginTop: '3rem', textAlign: 'left', background: 'rgba(255,255,255,0.02)', padding: '1.5rem', borderRadius: '8px' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Info size={20} /> Developer Note</h3>
        <p style={{ fontSize: '0.9rem' }}>
          To use the installer, you must compile `AX12A_Debug.ino` to a `.bin` file, place it in `public/firmware/`, and configure the `manifest.json`. If you already flashed the ESP32 manually via Arduino IDE, you can skip this step and go directly to the Dashboard.
        </p>
      </div>
    </div>
  );
}

export default Installer;
