import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from courier import AsyncCourier
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from agent import RUNS, run_and_notify
from notifications import send_welcome_email

# Load this project's .env only. A bare load_dotenv() also searches parent folders.
load_dotenv(Path(__file__).parent / ".env")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check the key at startup, before any request does per-user work.
    api_key = os.environ.get("COURIER_API_KEY")
    if not api_key:
        raise RuntimeError("COURIER_API_KEY is not set. Create .env with COURIER_API_KEY.")
    # One client for the app's lifetime, closed on shutdown.
    async with AsyncCourier(api_key=api_key) as courier:
        app.state.courier = courier
        yield


app = FastAPI(lifespan=lifespan)


def get_courier(request: Request) -> AsyncCourier:
    return request.app.state.courier


class User(BaseModel):
    id: str
    email: str


def current_user() -> User:
    # A demo user, so you can try this without auth. Read the signed-in user
    # from your session or database here.
    email = os.environ.get("DEMO_EMAIL")
    if not email:
        raise HTTPException(500, "DEMO_EMAIL is not set. Put your own email address in .env.")
    return User(id="user_123", email=email)


class Signup(BaseModel):
    name: str
    email: str


class AgentRunRequest(BaseModel):
    prompt: str


@app.post("/signup", status_code=202)
async def signup(
    body: Signup,
    background_tasks: BackgroundTasks,
    courier: Annotated[AsyncCourier, Depends(get_courier)],
):
    # Use your saved user's database id, so a repeat signup repeats its welcome key.
    user_id = f"user_{uuid.uuid4().hex}"
    # Runs after the response is sent, so signup never waits on Courier.
    background_tasks.add_task(send_welcome_email, courier, user_id, body.email, body.name)
    return {"user_id": user_id}


@app.post("/agent-runs", status_code=202)
async def start_agent_run(
    body: AgentRunRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(current_user)],
    courier: Annotated[AsyncCourier, Depends(get_courier)],
):
    run_id = uuid.uuid4().hex
    RUNS[run_id] = {"id": run_id, "user_id": user.id, "status": "running", "summary": None, "request_id": None}
    # The response returns now. The run, then its notification, happen after it.
    background_tasks.add_task(run_and_notify, courier, run_id, user.id, user.email, body.prompt)
    return RUNS[run_id]


@app.get("/agent-runs/{run_id}")
async def get_agent_run(run_id: str, user: Annotated[User, Depends(current_user)]):
    run = RUNS.get(run_id)
    # Only the user who started a run can read it.
    if run is None or run["user_id"] != user.id:
        raise HTTPException(404, "Run not found")
    return run
