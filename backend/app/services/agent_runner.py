"""
Agent Runner Service
--------------------
Orchestrates a full agent run:
  1. Builds the LangGraph graph (with the request-scoped DB session)
  2. Streams events from the graph — ONE pass, no double invocation
  3. Yields StreamChunk objects for the SSE endpoint
  4. Persists AgentRun + ToolCallLog rows after completion
  5. Fires the email webhook if the user has a webhook_email set
"""

import time
import uuid
from typing import AsyncGenerator

import structlog
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import AgentState, build_graph
from app.database.db import AgentRun, ToolCallLog, User
from app.schemas.agent import AgentQueryRequest, StreamChunk
from app.services import webhook as webhook_service

log = structlog.get_logger()

#orchestrator of the entire agent run
async def stream_agent(
    session: AsyncSession,
    user: User,
    request: AgentQueryRequest,
) -> AsyncGenerator[StreamChunk, None]:
    """
    Async generator — runs the agent once and yields StreamChunk objects.
    The FastAPI route formats each chunk as an SSE line.
    """
    run_id = uuid.uuid4()#unique ID for this request
    graph = build_graph(session) #creates your LangGraph agent

    # Build conversation history as LangChain message objects
    history_messages = []
    for msg in request.history:
        if msg.role == "user":
            history_messages.append(HumanMessage(content=msg.content))
        else:
            history_messages.append(AIMessage(content=msg.content))

    #starting memory of your agent
    initial_state: AgentState = {
        "messages": history_messages + [HumanMessage(content=request.query)],
        "tools_used": [],
        "fast_tokens": 0,
        "synth_tokens": 0,
        "iteration": 0,
    }

    # Accumulated during the single streaming pass. These are temporary variables to track 
    fast_tokens = 0 #reasoning cost
    synth_tokens = 0 #final answer cost
    tools_used: list[str] = [] #tools called
    tool_start_times: dict[str, float] = {}
    tool_logs: list[dict] = [] #detailed logs
    final_response = "" #full answer text

    try:
        #This is where your LangGraph actually runs
        async for event in graph.astream_events(initial_state, version="v2"): #This gives live streaming events
            kind = event["event"] #Each step of the graph emits events
            # langgraph_node tells us which node emitted this event
            node = event.get("metadata", {}).get("langgraph_node", "")

            # ── Stream tokens only from the synthesis node ─────────────────────
            if kind == "on_chat_model_stream" and node == "synthesis_node":
                chunk = event["data"].get("chunk")
                if chunk is None:
                    continue

                # Gemini returns content as a plain string on AIMessageChunk
                #If content is a string → use it directly, If content is a list → extract text from each part
                content = chunk.content
                if isinstance(content, str) and content:
                    final_response += content
                    yield StreamChunk(type="token", content=content)
                elif isinstance(content, list):
                    # Some models return a list of content parts
                    for part in content:
                        text = part if isinstance(part, str) else part.get("text", "")
                        if text:
                            final_response += text
                            yield StreamChunk(type="token", content=text) #stream to frontend

            # ── Accumulate token counts after each model call ──────────────────
            elif kind == "on_chat_model_end":
                output = event["data"].get("output")
                if output is not None:
                    usage = {}
                    if hasattr(output, "response_metadata"):
                        usage = output.response_metadata.get("usage_metadata", {})
                    elif isinstance(output, dict):
                        usage = output.get("response_metadata", {}).get("usage_metadata", {})
                    tokens = (usage.get("total_token_count") or usage.get("total_tokens") or 0)
                    if node == "synthesis_node":
                        synth_tokens += tokens
                        # Fallback: if Groq returned the whole response in one shot
                        # (non-streaming), on_chat_model_stream never fired and
                        # final_response is still empty. Capture it here and stream it.
                        if not final_response:
                            content = output.content if hasattr(output, "content") else ""
                            if isinstance(content, list):
                                content = "".join(
                                    p if isinstance(p, str) else p.get("text", "")
                                    for p in content
                                )
                            if content:
                                final_response = content
                                yield StreamChunk(type="token", content=content)
                    else:
                        fast_tokens += tokens

            # ── Tool started ───────────────────────────────────────────────────
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_start_times[tool_name] = time.monotonic()
                tools_used.append(tool_name)
                log.info("agent_runner.tool_start", tool=tool_name)
                yield StreamChunk(type="tool_call", content=tool_name)

            # ── Tool finished ──────────────────────────────────────────────────
            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                elapsed = time.monotonic() - tool_start_times.pop(tool_name, time.monotonic())
                tool_logs.append({
                    "tool_name": tool_name,
                    "input_data": event["data"].get("input") or {},
                    "output_data": {"result": str(event["data"].get("output", ""))},
                    "duration_ms": int(elapsed * 1000),
                })
                yield StreamChunk(type="tool_result", content=tool_name)

    except Exception as exc:
        msg = str(exc)
        if "rate_limit_exceeded" in msg or "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            import re
            wait = re.search(r"try again in ([\w\d .]+?)(?:\.|$)", msg)
            wait_str = wait.group(1).strip() if wait else None
            friendly = (
                f"The AI service is temporarily busy. Please wait {wait_str} and try again."
                if wait_str else
                "The AI service is temporarily busy. Please wait a moment and try again."
            )
            log.warning("agent_runner.rate_limit", run_id=str(run_id))
            yield StreamChunk(type="error", content=friendly, run_id=run_id)
        elif "timed out" in msg.lower() or "timeout" in msg.lower() or "deadline" in msg.lower():
            log.warning("agent_runner.timeout", run_id=str(run_id))
            yield StreamChunk(type="error", content="The AI took too long to respond. Please try again.", run_id=run_id)
        else:
            log.error("agent_runner.error", error=msg, run_id=str(run_id))
            yield StreamChunk(type="error", content=msg, run_id=run_id)
        return

    # ── Persist to database ────────────────────────────────────────────────────
    agent_run = AgentRun(
        id=run_id,
        user_id=user.id,
        query=request.query,
        response=final_response,
        tools_used=list(dict.fromkeys(tools_used)),  # deduplicate, preserve order
        haiku_tokens=fast_tokens,
        sonnet_tokens=synth_tokens,
        cost_usd=0.0,  # Gemini free tier
    )
    session.add(agent_run)

    for tl in tool_logs:
        session.add(ToolCallLog(
            run_id=run_id,
            tool_name=tl["tool_name"],
            input_data=tl["input_data"],
            output_data=tl["output_data"],
            duration_ms=tl["duration_ms"],
        ))

    await session.commit()
    log.info("agent_runner.saved", run_id=str(run_id), tools=tools_used)

    # ── Email webhook (fire-and-forget) ───────────────────────────────────────
    if user.webhook_email:
        await webhook_service.send_trip_summary(user, agent_run)

    yield StreamChunk(type="done", content="", run_id=run_id)
