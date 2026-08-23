from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core import get_system_stats, get_container_status, get_recent_incidents

app = FastAPI(title="MiniSentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHED_CONTAINER = "test-app"

@app.get("/status")
def status():
    stats = get_system_stats()
    container_status = get_container_status(WATCHED_CONTAINER)
    return {
        "system": stats,
        "container": {
            "name": WATCHED_CONTAINER,
            "status": container_status
        }
    }

@app.get("/incidents")
def incidents():
    return get_recent_incidents(limit=20)
