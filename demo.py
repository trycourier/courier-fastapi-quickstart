"""Start one agent run, wait for it to finish, and print Courier's request id.

FastAPI's TestClient runs the app in this process, so you don't need a server.
It finishes the background tasks before post() returns.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

if os.environ.get("COURIER_API_KEY", "") in ("", "YOUR_COURIER_API_KEY"):
    sys.exit("COURIER_API_KEY is not set. Copy .env.example to .env and add your key.")
email = os.environ.get("DEMO_EMAIL", "")
if email in ("", "YOUR_EMAIL"):
    sys.exit("DEMO_EMAIL is not set. Put your own email address in .env.")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

with TestClient(app) as client:
    response = client.post("/agent-runs", json={"prompt": "Summarize this week's support tickets"})
    response.raise_for_status()
    run_id = response.json()["id"]
    print(f"Started agent run {run_id} for user_123.")
    run = client.get(f"/agent-runs/{run_id}").json()

if not run["request_id"]:
    sys.exit(f"Run {run_id} is {run['status']}, but no notification went out. See the log above.")
print(run["summary"])
print(f"Notified {email} by email and inbox. Request id: {run['request_id']}")
