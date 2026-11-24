# Notifications for FastAPI, with Courier

A FastAPI app that sends notifications from background tasks, so no request waits on a send. It emails a welcome message on signup, and when a long-running AI agent task finishes, it notifies the user by email and in the Courier inbox with the result. Every send is one call to [Courier](https://www.courier.com) through the official Python SDK, [`trycourier`](https://pypi.org/project/trycourier/), using its `AsyncCourier` client.

This is the companion project for [Send notifications from a FastAPI app](https://www.courier.com/docs/guides/send-notifications-from-fastapi) in the Courier docs.

## Build it with a coding agent

Paste this into Claude Code, Cursor, or Codex from your own FastAPI project:

```text
Add notifications to this FastAPI app with Courier, including an email and inbox notification when an AI agent run finishes.
Follow https://www.courier.com/docs/guides/send-notifications-from-fastapi.md and the reference app at https://github.com/trycourier/courier-fastapi-quickstart.
Use the trycourier package (from courier import AsyncCourier) and read COURIER_API_KEY from the environment.
Queue every send with BackgroundTasks so the response returns first, and pass one idempotency key per event, such as agent-run-<run_id>-finished.
Route the agent-run notification to email and inbox together, and keep our existing email provider.
When done, add a demo command like the reference app's demo.py, run it, and show me the request id.
```

Install the Courier skill with `npx skills add trycourier/courier-skills`, and connect the [Courier MCP server](https://www.courier.com/docs/resources/mcp), so the agent can read Courier Logs and templates itself. `AGENTS.md` in this repo lists the rules it should keep.

## What it shows

- **The sends** in `notifications.py`. `send()` makes the one `client.send.message` call with an idempotency key, and logs a failure instead of raising it into a finished response.
- **A notify endpoint** in `main.py`. `POST /signup` queues a welcome email with `BackgroundTasks` and returns `202` right away.
- **The agent-run notification** in `agent.py`. `POST /agent-runs` in `main.py` starts a simulated agent run and returns. When the run finishes, `run_and_notify` sends the summary by email and to the inbox, keyed `agent-run-<run_id>-finished`.
- **A round trip** in `demo.py`. `python demo.py` starts one run, waits for it, and prints Courier's request id.

## Run it

You need Python 3.12 or newer and a [Courier account](https://app.courier.com/signup).

```bash
git clone https://github.com/trycourier/courier-fastapi-quickstart.git
cd courier-fastapi-quickstart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

- `COURIER_API_KEY`: your key from [Platform → API Keys](https://app.courier.com/settings/api-keys). A **Test** key is fine.
- `DEMO_EMAIL`: the address you signed up to Courier with. On a Test key, the built-in test email provider delivers only to members of your workspace.

Then run the demo:

```bash
python demo.py
```

You should see:

```text
INFO:notifications:Courier accepted agent-run-4e5d0a95dfd8...-finished, request id 1-6740a1b2-...
Started agent run 4e5d0a95dfd8... for user_123.
Done: Summarize this week's support tickets. Found 3 themes and drafted a summary for review.
Notified you@yourcompany.com by email and inbox. Request id: 1-6740a1b2-...
```

The email arrives a few seconds later. Open [Logs](https://app.courier.com/logs) in Courier to see both channels. To check your key on its own first, run `first_send.py` with the two values inline: `COURIER_API_KEY=... DEMO_EMAIL=... python first_send.py`.

To try the endpoints yourself, run `fastapi dev main.py` and open `localhost:8000/docs`.

## How the pieces fit

```
POST /agent-runs              FastAPI                                  Courier
     |--------------------------->| store run, status "running"          |
     |<-- 202 {"id": run_id} -----| queue run_and_notify (BackgroundTasks)
     |                            |                                      |
     |                            | await run_agent(prompt)   (3 s)      |
     |                            | status "finished", summary           |
     |                            |-- POST /send ------------------------->|  routing: all [email, inbox]
     |                            |   Idempotency-Key:                   |
     |                            |   agent-run-<run_id>-finished        |  deliver, log every attempt
     |                            |<------------------ requestId ----------|
GET /agent-runs/{run_id} -------->| {"status": "finished", "request_id": ...}
```

The run id is new for every run, so its key is too. A retry of one run's notification reuses the key, and Courier returns the first response instead of notifying twice.

## When a send fails

The send runs after the response went out, so no caller is left to see an error. The SDK retries connection errors, 429s, and 5xx responses twice with the same key. If the send still fails, `send()` logs it with the key and returns `None`, and the run's `request_id` stays `null`. Nothing retries it later. When a lost notification matters, queue the send in a worker (Celery, arq, or your platform's queue) and retry it with the same key.

## Adapting it to your app

**Take the user from your session.** `current_user()` in `main.py` returns a demo user, `user_123`, with `DEMO_EMAIL`. Replace it with your auth dependency, and keep the `user_id` stable so the inbox and preferences follow one person.

**Replace `run_agent` in `agent.py`.** It sleeps for three seconds and returns a summary. Call your agent framework there, and keep the notification after it.

**Store runs in your database.** `RUNS` is a dict, so it's lost on restart and isn't shared between workers.

**Show the inbox in your frontend.** The notification lands in the Courier inbox for `user_123`. Add the inbox UI with one of the [inbox guides](https://www.courier.com/docs/in-app/add-an-inbox), and mint its token for the signed-in user.

**Use a template.** The sends use inline `content`, so they run against a fresh workspace. In production, design the message in Courier and pass `"template": "<your template id>"` instead, keeping `data` as it is.

## Commands

| | |
|---|---|
| `python demo.py` | Start one agent run in-process and print the request id |
| `python first_send.py` | Send one email to `DEMO_EMAIL` (pass both values inline) |
| `fastapi dev main.py` | Run the API with reload on `localhost:8000` |

## Troubleshooting

**`demo.py` printed a request id but no email arrived.** Open the message in [Logs](https://app.courier.com/logs). On a Test key, `DEMO_EMAIL` has to be a member of your Courier workspace.

**`AuthenticationError: Error code: 401` in the log.** The key in `.env` is wrong, or it has a stray space. Copy it again.

**The run finished but `request_id` is `null`.** The send failed after the SDK's retries. The log line above it has the error and the idempotency key.

## Further reading

- [Send to the inbox](https://www.courier.com/docs/in-app/send-to-the-inbox)
- [Message routing](https://www.courier.com/docs/send/routing)
- [Idempotency](https://www.courier.com/docs/reference/api-overview#idempotency)
- [Send from an AI agent](https://www.courier.com/docs/guides/send-from-an-ai-agent)

## License

MIT
