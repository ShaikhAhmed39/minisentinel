import psutil

import subprocess

import time

import json

from datetime import datetime



INCIDENT_LOG = "incidents.log"



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

        if result.returncode == 0:

            return result.stdout.strip()

        else:

            return "not_found"

    except Exception as e:

        return f"error: {e}"



def restart_container(container_name):

    try:

        result = subprocess.run(

            ["docker", "restart", container_name],

            capture_output=True, text=True, timeout=15

        )

        return result.returncode == 0

    except Exception as e:

        return False



def log_incident(container_name, action, result):

    entry = {

        "timestamp": datetime.now().isoformat(),

        "container": container_name,

        "action": action,

        "result": result

    }

    with open(INCIDENT_LOG, "a") as f:

        f.write(json.dumps(entry) + "\n")

    print(f"[INCIDENT LOGGED] {entry}")



def check_and_heal(container_name):

    status = get_container_status(container_name)

    print(f"{container_name}: {status}")



    if status == "exited":

        print(f" {container_name} is down. Attempting recovery...")

        success = restart_container(container_name)



        time.sleep(2)

        new_status = get_container_status(container_name)



        if new_status == "running":

            log_incident(container_name, "restart", "success")

            print(f" Recovery successful.")

        else:

            log_incident(container_name, "restart", "failed")

            print(f" Recovery failed. Status: {new_status}")



if __name__ == "__main__":

    stats = get_system_stats()

    print("=== System Stats ===")

    print(f"CPU Usage:    {stats['cpu_percent']}%")

    print(f"Memory Usage: {stats['memory_percent']}%")

    print(f"Disk Usage:   {stats['disk_percent']}%")



    print("\n=== Container Health Check ===")

    check_and_heal("test-app")
