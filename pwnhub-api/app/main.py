from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import devices, handshakes
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="PwnHub API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(handshakes.router, prefix="/api/handshakes", tags=["handshakes"])


@app.get("/")
async def root():
    return {"message": "PwnHub API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}

