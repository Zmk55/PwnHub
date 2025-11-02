import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """Get the SQLite database path. Uses /data in Docker, ./data locally."""
    data_dir = Path("/data") if Path("/data").exists() else Path("./data")
    data_dir.mkdir(exist_ok=True)
    return data_dir / "pwnhub.db"


def init_db():
    """Initialize the SQLite database and create tables."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create devices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial TEXT UNIQUE NOT NULL,
            name TEXT,
            hostname TEXT,
            ssh_fp TEXT,
            image_gen INTEGER DEFAULT 0,
            handshake_count INTEGER DEFAULT 0,
            last_seen INTEGER,
            last_ip TEXT,
            ssh_provisioned INTEGER DEFAULT 0
        )
    """)
    
    # Add ssh_provisioned column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE devices ADD COLUMN ssh_provisioned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass

    # Create handshakes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS handshakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial TEXT NOT NULL,
            filename TEXT NOT NULL,
            bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (serial) REFERENCES devices(serial)
        )
    """)

    conn.commit()
    conn.close()
    return db_path


def get_conn():
    """Get a database connection."""
    db_path = get_db_path()
    return sqlite3.connect(str(db_path), check_same_thread=False)


def get_handshake_storage_path() -> Path:
    """Get the handshake storage path. Uses /srv/pwnhub in Docker, ./storage locally."""
    storage_dir = Path("/srv/pwnhub") if Path("/srv/pwnhub").exists() else Path("./storage")
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / "handshakes"

