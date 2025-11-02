"""
PwnHub Agent Plugin for Pwnagotchi
This plugin allows Pwnagotchi devices to register with a PwnHub server
and upload handshake files automatically.
"""

import logging
import requests
import json
import time
import threading
import subprocess
import socket
from pathlib import Path
import pwnagotchi.plugins as plugins


class PwnHub(plugins.Plugin):
    __author__ = 'PwnHub Team'
    __version__ = '1.0.0'
    __license__ = 'MIT'
    __description__ = 'Connect Pwnagotchi to PwnHub server for centralized management'

    def __init__(self):
        super().__init__()
        self.options = {
            'enabled': True,
            'hub_url': 'http://10.67.0.1:5000',
            'auth_token': '',
            'heartbeat_interval': 300,
            'push_handshakes': True,
            'upload_method': 'http',
            'handshake_path': '/root/handshakes',
            'agent_id_file': '/root/.pwnhub_agent_state.json',
            'log_level': 'INFO'
        }
        self.device_serial = None
        self.device_hostname = None
        self.device_ssh_fp = None
        self.device_machine_id = None
        self.image_gen = 0
        self.state_file = None
        self.state = {}
        self.background_thread = None
        self.running = False
        self.logger = logging.getLogger('PwnHub')

    def on_loaded(self):
        """Called when plugin is loaded."""
        # Set log level
        log_level = getattr(logging, self.options.get('log_level', 'INFO').upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        if not self.options.get('enabled', True):
            self.logger.info("Plugin disabled in config")
            return
        
        self.logger.info("Plugin loaded")
        
        # Initialize state file path
        self.state_file = Path(self.options.get('agent_id_file', '/root/.pwnhub_agent_state.json'))
        
        # Capture device identity
        try:
            self.device_serial = self.get_cpu_serial()
            self.device_hostname = self.get_hostname()
            self.device_ssh_fp = self.get_ssh_host_key_fingerprint()
            self.device_machine_id = self.get_machine_id()
            
            self.logger.info(f"Device serial: {self.device_serial}")
            self.logger.info(f"Device hostname: {self.device_hostname}")
        except Exception as e:
            self.logger.error(f"Error capturing device identity: {e}")
            return
        
        # Load saved state
        self.load_state()
        
        # Detect image generation
        self.detect_image_gen()
        
        # Save updated state
        self.save_state()
        
        # Start background thread
        self.running = True
        self.background_thread = threading.Thread(target=self._background_loop, daemon=True)
        self.background_thread.start()
        self.logger.info("Background thread started")

    def on_unload(self):
        """Called when plugin is unloaded."""
        self.running = False
        if self.background_thread:
            self.background_thread.join(timeout=5)
        self.logger.info("Plugin unloaded")

    def get_cpu_serial(self):
        """Read CPU serial from /proc/cpuinfo."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Serial' in line:
                        serial = line.split(':')[1].strip()
                        return serial
        except Exception as e:
            self.logger.warning(f"Could not read CPU serial: {e}")
        # Fallback: try device tree
        try:
            with open('/proc/device-tree/serial-number', 'r') as f:
                return f.read().strip()
        except:
            pass
        # Last fallback: use hostname-based identifier
        return socket.gethostname()

    def get_machine_id(self):
        """Read machine ID from /etc/machine-id."""
        try:
            with open('/etc/machine-id', 'r') as f:
                return f.read().strip()
        except Exception as e:
            self.logger.warning(f"Could not read machine-id: {e}")
            return None

    def get_ssh_host_key_fingerprint(self):
        """Get SSH host key fingerprint."""
        try:
            # Try ED25519 first (most common on Pwnagotchi)
            key_path = Path('/etc/ssh/ssh_host_ed25519_key.pub')
            if not key_path.exists():
                # Try RSA as fallback
                key_path = Path('/etc/ssh/ssh_host_rsa_key.pub')
            if not key_path.exists():
                # Try ECDSA
                key_path = Path('/etc/ssh/ssh_host_ecdsa_key.pub')
            
            if key_path.exists():
                result = subprocess.run(
                    ['ssh-keygen', '-lf', str(key_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Extract fingerprint (first token before the key type)
                    parts = result.stdout.strip().split()
                    if len(parts) >= 2:
                        return parts[1]  # Return fingerprint (SHA256:...)
        except Exception as e:
            self.logger.warning(f"Could not get SSH fingerprint: {e}")
        return None

    def get_hostname(self):
        """Get system hostname."""
        try:
            return socket.gethostname()
        except Exception as e:
            self.logger.warning(f"Could not get hostname: {e}")
            return "unknown"

    def get_handshake_count(self):
        """Count handshake files in handshake_path."""
        handshake_path = Path(self.options.get('handshake_path', '/root/handshakes'))
        if not handshake_path.exists():
            return 0
        
        extensions = ['.cap', '.pcap', '.hccapx']
        count = 0
        try:
            for file_path in handshake_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    count += 1
        except Exception as e:
            self.logger.warning(f"Error counting handshakes: {e}")
        
        return count

    def load_state(self):
        """Load state from agent_id_file."""
        if not self.state_file.exists():
            self.logger.info("State file does not exist, starting fresh")
            self.state = {}
            return
        
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
            self.logger.info("State loaded from file")
        except Exception as e:
            self.logger.error(f"Error loading state file: {e}")
            self.state = {}

    def save_state(self):
        """Save state to agent_id_file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            self.logger.debug("State saved to file")
        except Exception as e:
            self.logger.error(f"Error saving state file: {e}")

    def detect_image_gen(self):
        """Detect if this is a new image on the same hardware."""
        if not self.state:
            # No previous state, start at 0
            self.image_gen = 0
            return
        
        saved_serial = self.state.get('device_info', {}).get('serial')
        saved_machine_id = self.state.get('device_info', {}).get('machine_id')
        saved_ssh_fp = self.state.get('device_info', {}).get('ssh_fp')
        saved_image_gen = self.state.get('image_gen', 0)
        
        # Check if serial matches
        if saved_serial and saved_serial == self.device_serial:
            # Same hardware, check if image changed
            if (saved_machine_id and saved_machine_id != self.device_machine_id) or \
               (saved_ssh_fp and saved_ssh_fp != self.device_ssh_fp):
                # Image changed on same hardware
                self.image_gen = saved_image_gen + 1
                self.logger.info(f"Detected new image on same hardware, incrementing image_gen to {self.image_gen}")
            else:
                # Same image
                self.image_gen = saved_image_gen
        else:
            # Different hardware or first time
            self.image_gen = 0
        
        # Update state
        self.state['device_info'] = {
            'serial': self.device_serial,
            'machine_id': self.device_machine_id,
            'ssh_fp': self.device_ssh_fp
        }
        self.state['image_gen'] = self.image_gen

    def register_device(self):
        """Register this device with the hub."""
        hub_url = self.options.get('hub_url', 'http://10.67.0.1:5000')
        register_url = f"{hub_url}/api/devices/register"
        
        handshake_count = self.get_handshake_count()
        
        payload = {
            'serial': self.device_serial,
            'hostname': self.device_hostname,
            'ssh_fingerprint': self.device_ssh_fp,
            'image_gen': self.image_gen,
            'handshake_count': handshake_count
        }
        
        try:
            response = requests.post(
                register_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            self.logger.info(f"Device registered successfully: {response.status_code}")
            
            # Update state
            self.state['last_registered'] = int(time.time())
            self.save_state()
            
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error registering device: {e}")
            return False

    def send_heartbeat(self):
        """Send periodic heartbeat to hub."""
        hub_url = self.options.get('hub_url', 'http://10.67.0.1:5000')
        heartbeat_url = f"{hub_url}/api/devices/heartbeat"
        
        handshake_count = self.get_handshake_count()
        current_hostname = self.get_hostname()
        
        payload = {
            'serial': self.device_serial,
            'handshake_count': handshake_count
        }
        
        # Include hostname if it changed
        if current_hostname != self.device_hostname:
            payload['hostname'] = current_hostname
            self.device_hostname = current_hostname
        
        try:
            response = requests.post(
                heartbeat_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            self.logger.debug("Heartbeat sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error sending heartbeat: {e}")
            return False

    def upload_handshake_file(self, file_path):
        """Upload a handshake file to the hub."""
        hub_url = self.options.get('hub_url', 'http://10.67.0.1:5000')
        upload_url = f"{hub_url}/api/handshakes/upload"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/octet-stream')}
                data = {'serial': self.device_serial}
                
                response = requests.post(
                    upload_url,
                    files=files,
                    data=data,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get('status') == 'ok':
                    self.logger.info(f"Handshake uploaded successfully: {file_path.name}")
                    # Delete file on success
                    try:
                        file_path.unlink()
                        self.logger.info(f"Deleted local file: {file_path.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete file {file_path.name}: {e}")
                    return True
                else:
                    self.logger.error(f"Upload failed: {result}")
                    return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error uploading handshake {file_path.name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error uploading {file_path.name}: {e}")
            return False

    def sync_handshakes(self):
        """Walk handshake_path and upload any .cap/.pcap/.hccapx files."""
        if not self.options.get('push_handshakes', True):
            return
        
        if self.options.get('upload_method') != 'http':
            return
        
        handshake_path = Path(self.options.get('handshake_path', '/root/handshakes'))
        if not handshake_path.exists():
            return
        
        extensions = ['.cap', '.pcap', '.hccapx']
        
        try:
            for file_path in handshake_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    self.logger.info(f"Found handshake file: {file_path.name}")
                    self.upload_handshake_file(file_path)
        except Exception as e:
            self.logger.error(f"Error syncing handshakes: {e}")

    def _background_loop(self):
        """Background thread loop for periodic operations."""
        heartbeat_interval = self.options.get('heartbeat_interval', 300)
        
        # Register immediately on startup
        self.logger.info("Registering device on startup")
        self.register_device()
        
        # Initial handshake sync
        if self.options.get('push_handshakes', True):
            self.logger.info("Performing initial handshake sync")
            self.sync_handshakes()
        
        # Main loop
        while self.running:
            try:
                # Send heartbeat
                self.send_heartbeat()
                
                # Sync handshakes
                if self.options.get('push_handshakes', True):
                    self.sync_handshakes()
                
                # Sleep for heartbeat interval
                for _ in range(heartbeat_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error in background loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def on_handshake(self, agent, filename, access_point, client_station):
        """Called when a handshake is captured."""
        if not self.options.get('push_handshakes', True):
            return
        
        self.logger.info(f"Handshake captured: {filename}")
        
        # Find the handshake file
        handshake_path = Path(self.options.get('handshake_path', '/root/handshakes'))
        file_path = handshake_path / filename
        
        if file_path.exists():
            # Upload immediately
            self.upload_handshake_file(file_path)
        else:
            self.logger.warning(f"Handshake file not found: {file_path}")
