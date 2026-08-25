import psutil
import subprocess
import time
import json
import boto3
from datetime import datetime

INCIDENT_LOG = "incidents.log"
CONSECUTIVE_THRESHOLD = 3
COOLDOWN_SECONDS = 60
MAX_RETRIES = 3

SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:520519513966:minisentinel-alerts"
AWS_REGION = "ap-south-1"

# ⚠️ REPLACE with your actual bucket name if different
S3_BUCKET = "minisentinel-backups-ahmed"

sns_client = boto3.client('sns', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
cloudwatch_client = boto3.client('cloudwatch', region_name=AWS_REGION)

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


def send_alert(subject, message):
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
        print(f"[ALERT SENT] {subject}")
    except Exception as e:
        print(f"[ALERT FAILED] {e}")


def backup_to_s3():
    try:
        s3_client.upload_file(
            INCIDENT_LOG,
            S3_BUCKET,
            f"incidents/{datetime.now().strftime('%Y-%m-%d')}/incidents.log"
        )
        print("[S3 BACKUP] Success")
    except Exception as e:
        print(f"[S3 BACKUP FAILED] {e}")


def push_metrics_to_cloudwatch(stats):
    try:
        cloudwatch_client.put_metric_data(
            Namespace='MiniSentinel',
            MetricData=[
                {
                    'MetricName': 'CPUUtilization',
                    'Value': stats['cpu_percent'],
                    'Unit': 'Percent'
                },
                {
                    'MetricName': 'MemoryUtilization',
                    'Value': stats['memory_percent'],
                    'Unit': 'Percent'
                },
                {
                    'MetricName': 'DiskUtilization',
                    'Value': stats['disk_percent'],
                    'Unit': 'Percent'
                },
            ]
        )
        print("[CLOUDWATCH] Metrics pushed")
    except Exception as e:
        print(f"[CLOUDWATCH FAILED] {e}")


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

    if result in ("escalated", "failed"):
        send_alert(
            subject=f"MiniSentinel Alert: {container_name} - {result}",
            message=(
                f"Container: {container_name}\n"
                f"Action: {action}\n"
                f"Result: {result}\n"
                f"Details: {details}\n"
                f"Time: {entry['timestamp']}"
            )
        )

    backup_to_s3()


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
    print(f"⚠️  {container_name} down ({state['consecutive_down']}/{CONSECUTIVE_THRESHOLD} checks)")

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
