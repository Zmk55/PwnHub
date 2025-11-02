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

async function viewHandshakes(serial) {
    try {
        const response = await fetch(`${API_BASE}/api/handshakes/${encodeURIComponent(serial)}/list`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const handshakes = data.handshakes || [];
        
        // Create modal for handshake list
        showHandshakeModal(serial, handshakes);
    } catch (error) {
        console.error('Error loading handshakes:', error);
        showToast(`Error loading handshakes: ${error.message}`, 'error');
    }
}

function showHandshakeModal(serial, handshakes) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.id = 'handshake-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    // Format file size
    function formatBytes(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    // Format date
    function formatDate(dateStr) {
        if (!dateStr) return 'Unknown';
        const date = new Date(dateStr);
        return date.toLocaleString();
    }
    
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        padding: 20px;
        border-radius: 8px;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        width: 90%;
    `;
    
    modalContent.innerHTML = `
        <h2>Handshakes for Device: ${serial}</h2>
        <button onclick="closeHandshakeModal()" style="float: right; margin-bottom: 10px;">Close</button>
        ${handshakes.length === 0 
            ? '<p>No handshakes found for this device.</p>'
            : `
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr>
                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Filename</th>
                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Size</th>
                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Uploaded</th>
                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">SHA256</th>
                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${handshakes.map(h => `
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${h.filename}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${formatBytes(h.bytes)}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${formatDate(h.uploaded_at)}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-family: monospace; font-size: 10px;">${(h.sha256 || '').substring(0, 16)}...</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                                <a href="${API_BASE}/api/handshakes/${encodeURIComponent(serial)}/download/${encodeURIComponent(h.filename)}" 
                                   download="${h.filename}"
                                   style="color: #4CAF50; text-decoration: none;">Download</a>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `}
    `;
    
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeHandshakeModal();
        }
    });
}

function closeHandshakeModal() {
    const modal = document.getElementById('handshake-modal');
    if (modal) {
        modal.remove();
    }
}

async function backupDevice(serial) {
    if (!confirm(`Create backup for device ${serial}? This will create a tarball of all handshake files.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/devices/${encodeURIComponent(serial)}/backup`, {
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
        
        // Show success toast
        showToast(`Backup created: ${result.filename} (${formatBytes(result.size_bytes)})`, 'success');
        
    } catch (error) {
        console.error('Error creating backup:', error);
        showToast(`Error creating backup: ${error.message}`, 'error');
    }
}

function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function showToast(message, type = 'info') {
    // Remove existing toasts
    const existing = document.querySelectorAll('.toast');
    existing.forEach(t => t.remove());
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 4px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        z-index: 2000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease-out;
    `;
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
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
        
        // Show success toast
        showToast(`SSH key provisioned successfully to device ${serial}`, 'success');
        
        // Reload devices list to update UI
        loadDevices();
        
    } catch (error) {
        console.error('Error provisioning SSH key:', error);
        showToast(`Error provisioning SSH key: ${error.message}`, 'error');
    }
}

// Load devices on page load
document.addEventListener('DOMContentLoaded', loadDevices);

// Refresh every 5 seconds
setInterval(loadDevices, 5000);

