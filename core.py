import psutil
import subprocess
import time
import json
from datetime import datetime

INCIDENT_LOG = "incidents.log"
CONSECUTIVE_THRESHOLD = 3
COOLDOWN_SECONDS = 60
MAX_RETRIES = 3

container_state = {}

def get_system_stats():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent
    }

def get_container_status(container_name):
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "not_found"
    except Exception:
        return "error"

def restart_container(container_name):
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False

def log_incident(container_name, action, result, details=""):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "container": container_name,
        "action": action,
        "result": result,
        "details": details
    }
    with open(INCIDENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[LOGGED] {entry}")

def get_recent_incidents(limit=20):
    incidents = []
    try:
        with open(INCIDENT_LOG, "r") as f:
            lines = f.readlines()
        for line in lines[-limit:]:
            incidents.append(json.loads(line))
        incidents.reverse()
    except FileNotFoundError:
        pass
    return incidents

def init_state(container_name):
    if container_name not in container_state:
        container_state[container_name] = {
            "consecutive_down": 0,
            "last_restart_time": None,
            "retry_count": 0,
            "escalated": False
        }

def check_and_heal(container_name):
    init_state(container_name)
    state = container_state[container_name]
    status = get_container_status(container_name)
    print(f"{container_name}: {status}")

    if status == "running":
        state["consecutive_down"] = 0
        state["retry_count"] = 0
        state["escalated"] = False
        return

    state["consecutive_down"] += 1
    print(f"{container_name} down ({state['consecutive_down']}/{CONSECUTIVE_THRESHOLD} checks)")

    if state["consecutive_down"] < CONSECUTIVE_THRESHOLD:
        return
    if state["escalated"]:
        return

    now = time.time()
    if state["last_restart_time"] and (now - state["last_restart_time"]) < COOLDOWN_SECONDS:
        return

    if state["retry_count"] >= MAX_RETRIES:
        state["escalated"] = True
        log_incident(container_name, "restart", "escalated",
                     f"Gave up after {MAX_RETRIES} failed attempts.")
        return

    restart_container(container_name)
    state["last_restart_time"] = time.time()
    state["retry_count"] += 1

    time.sleep(2)
    new_status = get_container_status(container_name)

    if new_status == "running":
        log_incident(container_name, "restart", "success")
        state["consecutive_down"] = 0
        state["retry_count"] = 0
    else:
        log_incident(container_name, "restart", "failed", f"Status after restart: {new_status}")
