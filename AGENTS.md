# Courier FastAPI quickstart

A FastAPI app on Python 3.12 that sends notifications through Courier from background tasks: a welcome email on signup, and an email plus inbox message when a simulated AI agent run finishes. Guide: https://www.courier.com/docs/guides/send-notifications-from-fastapi

## Commands

- Install: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Set up: `cp .env.example .env`, then add `COURIER_API_KEY` and `DEMO_EMAIL`
- First send: `COURIER_API_KEY=... DEMO_EMAIL=... python first_send.py` (prints a request id)
- Demo: `python demo.py` (runs one agent run in-process, prints the request id)
- Server: `fastapi dev main.py`, then open `localhost:8000/docs`

## Environment

Read from `.env` next to `main.py` (python-dotenv, explicit path). Never commit `.env`.

- `COURIER_API_KEY`: checked in `main.py`'s lifespan, which creates the one `AsyncCourier` client. Server-side only.
- `DEMO_EMAIL`: the demo user's address, read in `current_user()` and `demo.py`.

## Files that matter

- `notifications.py`: `send()` (the one `client.send.message` call, logs failures), `send_welcome_email`, `notify_agent_run_finished`.
- `agent.py`: `run_agent` (the simulated agent) and `run_and_notify`, the background task that notifies when a run finishes. `RUNS` is the in-memory run store.
- `main.py`: lifespan client, `current_user()` demo user, `POST /signup`, `POST /agent-runs`, `GET /agent-runs/{run_id}`.
- `demo.py`: drives `POST /agent-runs` through `TestClient` and prints the request id.
- `first_send.py`: the standalone send from the top of the guide.

## Rules

- Use the `trycourier` package: `from courier import AsyncCourier` in the app, `Courier` only in `first_send.py`.
- Read the key from `COURIER_API_KEY`. Never hard-code it or return it to a client.
- Queue sends with `BackgroundTasks.add_task`. Never await Courier before returning a response.
- One idempotency key per event: `welcome-<user_id>` per saved user, `agent-run-<run_id>-finished` per agent run.
- A failed send is logged in `send()` and the run's `request_id` stays `None`. Nothing retries it after the SDK's two retries.
- Take the user from `current_user()` (the session in a real app), never from the request body.
- Don't call an email provider SDK directly. Courier routes to the providers connected in the workspace.
