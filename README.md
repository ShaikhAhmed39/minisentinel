# 🛡️ MiniSentinel

**A self-healing cloud infrastructure monitoring system — detects failures on AWS and recovers them automatically, without human intervention.**

MiniSentinel watches a Docker container's health in real time. When it goes down, MiniSentinel confirms the failure isn't a false alarm, attempts recovery with safe retry limits, verifies the fix actually worked, logs everything, backs it up to the cloud, and emails a human the moment it's genuinely stuck.

---

## 🎥 Demo
### Self-healing recovery
sha256:56650f202fe3efcc00505d9838c0f823b1832e95edebebb80f0a1ea4454fa2dd

### Escalation and alerting


---

## Why this exists

Modern applications fail in small, predictable ways — a container crashes, a process hangs. Traditionally, someone has to notice, log in, diagnose, and manually restart it. MiniSentinel automates that entire loop:

```
MONITOR → DETECT → CONFIRM → RECOVER → VERIFY → LOG → ALERT
```

It also knows its own limits — after a fixed number of failed recovery attempts, it stops trying and escalates to a human instead of looping forever.

---

## Key Features

- **Real-time health monitoring** — CPU, memory, disk, and Docker container status
- **Confirmation-based detection** — requires 3 consecutive bad readings before acting, avoiding false alarms from temporary blips
- **Automated recovery** — restarts failed containers, with a cooldown period to prevent restart loops
- **Retry limits & escalation** — gives up gracefully after 3 failed attempts and alerts a human, rather than looping forever
- **Live dashboard** — auto-refreshing web UI showing current status and incident history
- **Email alerts via Amazon SNS** — notified the moment something needs attention
- **Automated backups to Amazon S3** — every incident is archived, organized by date
- **Native AWS metrics via CloudWatch** — system stats pushed to a custom CloudWatch namespace
- **Secure by design** — EC2 uses an IAM Role for AWS access, no credentials stored on the server

---

## Architecture

```
Laptop (dev) ──git push/pull──▶ GitHub ──git clone/pull──▶ EC2 (AWS, Mumbai)
                                                                 │
                                                    ┌────────────┼────────────┐
                                                    ▼            ▼            ▼
                                                 Docker      monitor.py    api.py
                                              (test-app)   (detect+heal)  (FastAPI)
                                                                 │            │
                                                    ┌────────────┼─────┐      │
                                                    ▼            ▼     ▼      ▼
                                                  SNS           S3  CloudWatch  Browser
                                              (email alert)  (backup) (metrics) (dashboard)
```

---

## Tech Stack

**Backend:** Python, FastAPI, `psutil`, `boto3`
**Infrastructure:** AWS EC2, Docker, IAM Roles
**Observability:** Amazon CloudWatch, Amazon SNS, Amazon S3
**Frontend:** HTML, CSS, JavaScript
**DevOps:** Git, GitHub, Linux (Ubuntu/WSL2), Bash

---

## Project Structure

```
minisentinel/
├── core.py              # Shared logic: monitoring, recovery, alerts, backups, metrics
├── monitor.py            # Standalone loop: continuously checks and heals
├── api.py                 # FastAPI backend exposing /status and /incidents
├── dashboard/
│   └── index.html          # Live-updating web dashboard
├── config.yaml              # Configurable thresholds
├── requirements.txt          # Python dependencies
└── incidents.log               # Generated incident history (gitignored)
```

---

## How It Works

1. `monitor.py` checks system stats and the target container's status every 10 seconds
2. If the container is down for 3 consecutive checks, recovery begins
3. MiniSentinel attempts a restart, waits, then verifies the container is genuinely healthy again — never assumes success
4. Every outcome (success, failure, or escalation) is logged, backed up to S3, and pushed to CloudWatch
5. If an outcome is a failure or escalation, an email alert fires via SNS
6. After 3 failed attempts, MiniSentinel stops trying and marks the incident as **escalated** — a human needs to look
7. The dashboard (`api.py` + `dashboard/index.html`) shows all of this live, refreshing every 5 seconds

---

## Setup

### Local (development)

```bash
git clone https://github.com/ShaikhAhmed39/minisentinel.git
cd minisentinel
pip install -r requirements.txt --break-system-packages
docker run -d --name test-app nginx
python3 -m uvicorn api:app --reload --port 8000
```

In a separate terminal:
```bash
python3 monitor.py
```

Open `dashboard/index.html` in a browser (update `API_URL` if not running locally).

### AWS Deployment

1. Launch an EC2 instance (Ubuntu, t3.micro — free tier eligible)
2. Attach an IAM Role with `AmazonSNSFullAccess`, `AmazonS3FullAccess`, `CloudWatchFullAccess`
3. Install Docker and Python on the instance
4. Clone this repo and install dependencies
5. Open port 8000 in the instance's Security Group
6. Run the API and monitor with `nohup ... -u ... &` to keep them alive after disconnecting
7. Point `dashboard/index.html`'s `API_URL` at the instance's public IP

---

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/status` | Current system stats and container health |
| GET | `/incidents` | Recent incident history (detection, recovery, escalation) |

---

## Design Decisions Worth Noting

- **Why confirm before acting?** A single bad reading can be a temporary blip. Requiring 3 consecutive failures avoids restarting a healthy container unnecessarily.
- **Why a cooldown between restarts?** Prevents restart loops — a container that keeps failing shouldn't be restarted every few seconds forever.
- **Why escalate instead of retrying forever?** A responsible automation system knows when a problem is beyond its own ability to fix, and hands off to a human rather than looping indefinitely.
- **Why an IAM Role instead of access keys on the server?** Storing AWS credentials on a server is a security risk if that server is ever compromised. An IAM Role grants the same permissions without any secret ever living on disk.

---

## Author

**Ahmed Shaikh**
[GitHub](https://github.com/ShaikhAhmed39) • [LinkedIn](https://www.linkedin.com/in/ahmed-shaikh-54b6b7276)

---

## License

This project is for educational and portfolio purposes.
