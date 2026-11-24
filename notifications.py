import logging

from courier import AsyncCourier, CourierError

logger = logging.getLogger(__name__)


async def send(courier: AsyncCourier, message: dict, idempotency_key: str) -> str | None:
    """Send one message through Courier. Returns the request id, or None if the send failed."""
    try:
        response = await courier.send.message(message=message, idempotency_key=idempotency_key)
    except CourierError:
        # This runs in a background task after the response went out, so no
        # caller sees the error. The SDK retries twice with this key, but Courier
        # replays a stored 4xx or 5xx for that key, so only a timeout, a
        # connection error, or a 429 can succeed on a retry, once the key's
        # 60-second lock clears. This demo only logs the failure. To retry those
        # later, queue the send in a worker.
        logger.exception("Courier send failed, idempotency key %s", idempotency_key)
        return None
    logger.info("Courier accepted %s, request id %s", idempotency_key, response.request_id)
    return response.request_id


async def send_welcome_email(courier: AsyncCourier, user_id: str, email: str, name: str) -> str | None:
    return await send(
        courier,
        message={
            "to": {"user_id": user_id, "email": email},
            "content": {"title": "Welcome to Acme, {{name}}", "body": "Your account is ready."},
            "routing": {"method": "single", "channels": ["email"]},
            "data": {"name": name},
        },
        # Covers the SDK's retries of this send. Pass your saved user's id, so a
        # repeat signup for the same user reuses the key.
        idempotency_key=f"welcome-{user_id}",
    )


async def notify_agent_run_finished(
    courier: AsyncCourier, user_id: str, email: str, run_id: str, summary: str
) -> str | None:
    return await send(
        courier,
        message={
            "to": {"user_id": user_id, "email": email},
            # The summary goes in data, so text the agent wrote is never read as a template.
            "content": {"title": "Your agent run finished", "body": "{{summary}}"},
            # Email and the Courier inbox at once. The inbox shows it to user_id.
            "routing": {"method": "all", "channels": ["email", "inbox"]},
            "data": {"summary": summary, "run_id": run_id},
        },
        # One key per run. A retry returns the first response instead of
        # notifying twice, and the next run gets a new key.
        idempotency_key=f"agent-run-{run_id}-finished",
    )
