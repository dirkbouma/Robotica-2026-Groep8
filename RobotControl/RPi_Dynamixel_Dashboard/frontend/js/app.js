const API_BASE = "http://localhost:8000/api";
const WS_URL = "ws://localhost:8000/ws";

let currentServoId = null;
let socket = null;
let isScanning = false;

// DOM Elements
const btnScan = document.getElementById('btn-scan');
const servoList = document.getElementById('servo-list');
const wsStatusDot = document.getElementById('ws-status-dot');
const wsStatusText = document.getElementById('ws-status-text');
const mainGrid = document.getElementById('main-grid');
const selectedServoTitle = document.getElementById('selected-servo-title');

const telPos = document.getElementById('tel-pos');
const telLoad = document.getElementById('tel-load');
const telVolt = document.getElementById('tel-volt');
const telTemp = document.getElementById('tel-temp');

const rangePosition = document.getElementById('range-position');
const valPosition = document.getElementById('val-position');
const toggleTorque = document.getElementById('toggle-torque');
const btnRefreshRegs = document.getElementById('btn-refresh-regs');
const tbodyRegisters = document.querySelector('#register-table tbody');

// Initialize
function init() {
    setupWebSocket();
    setupEventListeners();
}

function setupWebSocket() {
    socket = new WebSocket(WS_URL);
    
    socket.onopen = () => {
        wsStatusDot.classList.add('connected');
        wsStatusText.textContent = 'Connected';
        // Send request to monitor current servo if selected
        updateWsSubscription();
    };

    socket.onclose = () => {
        wsStatusDot.classList.remove('connected');
        wsStatusText.textContent = 'Disconnected';
        setTimeout(setupWebSocket, 3000); // Reconnect loop
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (currentServoId && data[currentServoId]) {
            const telemetry = data[currentServoId];
            telPos.textContent = telemetry["Present Position"];
            // Convert load (0-1023 CCW, 1024-2047 CW) to rough percentage
            let loadRaw = telemetry["Present Load"];
            let loadPercent = (loadRaw > 1023 ? loadRaw - 1024 : loadRaw) / 10.23;
            telLoad.textContent = loadPercent.toFixed(1);
            
            telVolt.textContent = (telemetry["Present Voltage"] / 10).toFixed(1);
            telTemp.textContent = telemetry["Present Temperature"];
            
            // Sync slider if not actively dragging
            if (document.activeElement !== rangePosition) {
                rangePosition.value = telemetry["Present Position"];
                valPosition.textContent = telemetry["Present Position"];
            }
        }
    };
}

function updateWsSubscription() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            servo_ids: currentServoId ? [currentServoId] : []
        }));
    }
}

function setupEventListeners() {
    btnScan.addEventListener('click', scanServos);
    
    rangePosition.addEventListener('input', (e) => {
        valPosition.textContent = e.target.value;
    });

    rangePosition.addEventListener('change', async (e) => {
        if (!currentServoId) return;
        const val = parseInt(e.target.value);
        await fetch(`${API_BASE}/servo/move`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ servo_id: currentServoId, goal_position: val })
        });
    });

    toggleTorque.addEventListener('change', async (e) => {
        if (!currentServoId) return;
        await fetch(`${API_BASE}/servo/torque`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ servo_id: currentServoId, enable: e.target.checked })
        });
    });

    btnRefreshRegs.addEventListener('click', () => {
        if (currentServoId) loadRegisters(currentServoId);
    });

    document.getElementById('btn-torque-all-off').addEventListener('click', async () => {
        // Find all servos in list
        const items = servoList.querySelectorAll('li[data-id]');
        for (let item of items) {
            const id = parseInt(item.dataset.id);
            await fetch(`${API_BASE}/servo/torque`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ servo_id: id, enable: false })
            });
        }
        if (currentServoId) {
            toggleTorque.checked = false;
        }
        alert("Torque disabled for all detected servos.");
    });
}

async function scanServos() {
    if (isScanning) return;
    isScanning = true;
    btnScan.textContent = "Scanning...";
    
    try {
        const res = await fetch(`${API_BASE}/scan`);
        const data = await res.json();
        
        servoList.innerHTML = '';
        if (data.found_ids.length === 0) {
            servoList.innerHTML = '<li class="empty-msg">No servos found.</li>';
        } else {
            data.found_ids.forEach(id => {
                const li = document.createElement('li');
                li.innerHTML = `<span>ID: ${id}</span> <span class="badge">AX-12A</span>`;
                li.dataset.id = id;
                li.addEventListener('click', () => selectServo(id, li));
                servoList.appendChild(li);
            });
        }
    } catch (e) {
        console.error(e);
        alert("Failed to scan. Is backend running?");
    } finally {
        isScanning = false;
        btnScan.textContent = "Scan Servos";
    }
}

async function selectServo(id, liElement) {
    currentServoId = id;
    
    // Update active class
    const items = servoList.querySelectorAll('li');
    items.forEach(el => el.classList.remove('active'));
    liElement.classList.add('active');

    // Update UI
    selectedServoTitle.textContent = `Servo ID: ${id}`;
    mainGrid.style.display = 'grid';
    
    // Subscribe to telemetry
    updateWsSubscription();
    
    // Load registers
    await loadRegisters(id);
}

const CONTROL_TABLE_MAP = {
    // A small subset mapping name -> address just for display ordering, 
    // real data comes from backend as { "Model Number": 12, ... }
};

async function loadRegisters(id) {
    try {
        const res = await fetch(`${API_BASE}/servo/${id}/registers`);
        const data = await res.json();
        
        tbodyRegisters.innerHTML = '';
        
        // Sort keys
        const keys = Object.keys(data).sort();
        
        keys.forEach(key => {
            const val = data[key];
            const tr = document.createElement('tr');
            
            // Address lookup (mocked here, ideally backend sends this too)
            let addrHtml = `<span class="reg-addr">-</span>`;
            
            tr.innerHTML = `
                <td>${addrHtml}</td>
                <td>${key}</td>
                <td>
                    <input type="number" class="reg-input" value="${val}" id="reg-${key.replace(/\s+/g, '-')}">
                </td>
                <td>
                    <button class="btn secondary small" onclick="updateRegister('${key}')">Write</button>
                </td>
            `;
            tbodyRegisters.appendChild(tr);

            // Sync quick controls
            if (key === "Torque Enable") toggleTorque.checked = val === 1;
        });

    } catch (e) {
        console.error("Failed to load registers", e);
    }
}

window.updateRegister = async function(regName) {
    if (!currentServoId) return;
    
    const inputId = `reg-${regName.replace(/\s+/g, '-')}`;
    const inputEl = document.getElementById(inputId);
    const val = parseInt(inputEl.value);
    
    try {
        const res = await fetch(`${API_BASE}/servo/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                servo_id: currentServoId,
                register_name: regName,
                value: val
            })
        });
        const data = await res.json();
        if (!data.success) {
            alert("Failed to write register.");
        }
    } catch(e) {
        alert("Error writing register.");
    }
};

// Start
init();
