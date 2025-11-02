// Format unix timestamp to readable date/time
function formatLastSeen(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp * 1000); // Convert unix timestamp to milliseconds
    return date.toLocaleString();
}

// Determine API base URL based on whether we're in Docker (nginx proxy) or standalone
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')
    ? 'http://localhost:5000'
    : `http://${window.location.hostname}:5000`;

// Fetch devices from API
async function loadDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/devices`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const devices = await response.json(); // API returns list directly
        displayDevices(devices);
    } catch (error) {
        console.error('Error loading devices:', error);
        const loading = document.getElementById('loading');
        if (loading) {
            loading.textContent = 'Error loading devices.';
        }
    }
}

// Display devices in table
function displayDevices(devices) {
    const tbody = document.getElementById('devices-body');
    const table = document.getElementById('devices-table');
    const loading = document.getElementById('loading');
    
    if (loading) {
        loading.style.display = 'none';
    }
    
    if (!devices || devices.length === 0) {
        if (table) {
            table.style.display = 'none';
        }
        if (loading) {
            loading.textContent = 'No devices yet';
            loading.style.display = 'block';
        }
        return;
    }
    
    if (table) {
        table.style.display = 'table';
    }
    
    tbody.innerHTML = devices.map(device => {
        const serial = device.serial || 'N/A';
        const hostname = device.hostname || 'Unknown';
        const lastSeen = formatLastSeen(device.last_seen);
        const handshakeCount = device.handshake_count || 0;
        const sshProvisioned = device.ssh_provisioned || false;
        
        // Status icon for provisioned devices
        const statusIcon = sshProvisioned 
            ? '<span style="color: green;" title="SSH Key Provisioned">✓</span>' 
            : '<span style="color: orange;" title="SSH Key Not Provisioned">⚠</span>';
        
        // Provision button (only show if not provisioned)
        const provisionButton = sshProvisioned 
            ? '' 
            : `<button onclick="provisionDevice('${serial}')" style="background-color: #4CAF50; color: white;">Approve + Push Key</button>`;
        
        // SSH button (only enable if provisioned)
        const sshButton = sshProvisioned
            ? `<button onclick="connectDevice('${serial}')">SSH</button>`
            : `<button onclick="connectDevice('${serial}')" disabled title="SSH key must be provisioned first">SSH</button>`;
        
        return `
            <tr>
                <td>${serial}</td>
                <td>${hostname}</td>
                <td>${lastSeen}</td>
                <td>${handshakeCount}</td>
                <td>${statusIcon}</td>
                <td>
                    ${provisionButton}
                    ${sshButton}
                    <button onclick="viewHandshakes('${serial}')">Files</button>
                    <button onclick="backupDevice('${serial}')">Backup</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Placeholder functions for device actions
function connectDevice(serial) {
    // Open ttyd terminal page with serial parameter
    window.open(`/ttyd.html?serial=${encodeURIComponent(serial)}`, '_blank');
}

function viewHandshakes(serial) {
    // TODO: Implement handshake viewer
    alert(`View handshakes for: ${serial}`);
}

function backupDevice(serial) {
    // TODO: Implement device backup
    alert(`Backup device: ${serial}`);
}

async function provisionDevice(serial) {
    if (!confirm(`Provision SSH key to device ${serial}? This will push the hub's public key to the device.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/devices/${encodeURIComponent(serial)}/provision-ssh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Show success message
        alert(`SSH key provisioned successfully to device ${serial}`);
        
        // Reload devices list to update UI
        loadDevices();
        
    } catch (error) {
        console.error('Error provisioning SSH key:', error);
        alert(`Error provisioning SSH key: ${error.message}`);
    }
}

// Load devices on page load
document.addEventListener('DOMContentLoaded', loadDevices);

// Refresh every 5 seconds
setInterval(loadDevices, 5000);

