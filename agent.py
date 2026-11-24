import asyncio

from courier import AsyncCourier

from notifications import notify_agent_run_finished

# Runs live in memory for the demo. Keep them in your database: a dict is lost
# on restart and isn't shared between workers.
RUNS: dict[str, dict] = {}


async def run_agent(prompt: str) -> str:
    """Stand-in for your agent. Replace it with your agent framework's call."""
    await asyncio.sleep(3)
    return f"Done: {prompt}. Found 3 themes and drafted a summary for review."


async def run_and_notify(courier: AsyncCourier, run_id: str, user_id: str, email: str, prompt: str) -> None:
    """Run the agent, then tell the user it finished. FastAPI runs this as a background task."""
    try:
        summary = await run_agent(prompt)
    except Exception:
        # A failed run notifies nobody here. Send a "run failed" message the
        # same way if your users need one.
        RUNS[run_id]["status"] = "failed"
        raise
    RUNS[run_id].update(status="finished", summary=summary)
    # None when the send failed. send() in notifications.py logged why.
    RUNS[run_id]["request_id"] = await notify_agent_run_finished(courier, user_id, email, run_id, summary)
