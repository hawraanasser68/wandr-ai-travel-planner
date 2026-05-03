"""
Agent Routes
------------
POST /agent/chat              — run the agent, stream response as SSE
GET  /agent/runs              — list current user's past runs (paginated)
GET  /agent/runs/{id}         — get a single run with full response
POST /agent/runs/{id}/email   — email a completed plan to a given address
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_session
from app.database.db import AgentRun, User
from app.schemas.agent import AgentQueryRequest, AgentRunResponse
from app.services.agent_runner import stream_agent
from app.services.webhook import send_to_email

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
async def chat(
    request: AgentQueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Stream the agent's response as Server-Sent Events (SSE).

    Each event is a JSON line:
      data: {"type": "token",       "content": "Here are", "run_id": null}
      data: {"type": "tool_call",   "content": "rag_retriever", "run_id": null}
      data: {"type": "tool_result", "content": "rag_retriever", "run_id": null}
      data: {"type": "done",        "content": "", "run_id": "uuid"}
      data: {"type": "error",       "content": "...", "run_id": "uuid"}

    The frontend reads `type` to decide how to handle each event.
    """

    async def event_generator():
        async for chunk in stream_agent(session, current_user, request):
            yield f"data: {chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent nginx / proxies from buffering the stream
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_runs(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the authenticated user's agent run history, newest first."""
    result = await session.execute(
        select(AgentRun)
        .where(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(min(limit, 100))   # cap at 100 to prevent large result sets
        .offset(offset)
    )
    runs = result.scalars().all()
    return [AgentRunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return a single run — only if it belongs to the current user."""
    result = await session.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == current_user.id,  # ownership check
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return AgentRunResponse.model_validate(run)


class EmailRequest(BaseModel):
    email: EmailStr


@router.post("/runs/{run_id}/email", status_code=202)
async def email_run(
    run_id: uuid.UUID,
    body: EmailRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Send a completed trip plan to the given email address."""
    result = await session.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == current_user.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    await send_to_email(current_user, run, body.email)
    return {"message": f"Plan sent to {body.email}"}
