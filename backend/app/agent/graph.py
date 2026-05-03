"""
LangGraph Agent — Two-Model Routing
-------------------------------------
Flow:
  START
    └─► agent_node  (fast model — decides which tools to call)
          ├─► tool_node  (executes tools, enforces allowlist)  ──► agent_node (loop)
          └─► synthesis_node  (synth model — writes final travel plan)
                └─► END

Provider is controlled by LLM_PROVIDER env var:
  - "groq"   → uses Groq (Llama 3.3 70B) — free, no credit card
  - "gemini" → uses Google Gemini Flash — free tier
"""

import operator
from typing import Annotated, TypedDict
import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.prompts import REACT_SYSTEM, SYNTHESIS_SYSTEM
from app.agent.tools.registry import ALLOWED_TOOLS, build_tools
from app.config import get_settings

log = structlog.get_logger()

# Safety cap — prevents runaway loops if the model keeps calling tools
MAX_ITERATIONS = 4

# ALLOWED_TOOLS is now derived from the registry — no manual sync needed

# ── Graph state ────────────────────────────────────────────────────────────────

#shared memory object that flows through your LangGraph. Every node: reads it, updates it, and passes it forward
class AgentState(TypedDict): #This is the shared memory across the graph
    messages: Annotated[list[BaseMessage], operator.add]  # append-only across nodes A list of all conversation messages Includes: user messages, AI responses, and tool outputs
    tools_used: Annotated[list[str], operator.add]        # accumulate tool names
    fast_tokens: int     # tokens used by the ReAct loop model
    synth_tokens: int    # tokens used by the synthesis model
    iteration: int       # how many times agent_node has run



# ── Node: ReAct loop (fast model) ─────────────────────────────────────────────
async def agent_node(state: AgentState, fast_llm) -> dict:
    """
    Calls the fast model with tools bound.
    The model either returns tool calls (continue looping) or a plain message
    (signal to move to synthesis).
    """
    messages = [HumanMessage(content=REACT_SYSTEM)] + state["messages"]

    response: AIMessage = await fast_llm.ainvoke(messages)

    # Extract token usage (field names differ between Groq and Gemini)
    usage = response.response_metadata.get("usage_metadata") or \
            response.response_metadata.get("token_usage") or {}
    new_tokens = (usage.get("total_token_count") #new_tokens represents the number of tokens consumed in a single LLM call
                  or usage.get("total_tokens")
                  or 0)

    log.info(
        "agent.react_node",
        iteration=state["iteration"] + 1,
        has_tool_calls=bool(response.tool_calls),
        tokens=new_tokens,
    )

    return {
        "messages": [response],
        "fast_tokens": state["fast_tokens"] + new_tokens,
        "iteration": state["iteration"] + 1,
    }


# ── Node: Tool execution with allowlist ───────────────────────────────────────
def make_tool_node(tools: list):
    """
    Wraps LangGraph's ToolNode with an allowlist check.
    Any tool call whose name is not in ALLOWED_TOOLS gets replaced with
    an error ToolMessage — the model sees the error and can recover.
    """
    inner = ToolNode(tools)

    #
    async def tool_node(state: AgentState) -> dict:
        last_message: AIMessage = state["messages"][-1]
        tool_names_called = [tc["name"] for tc in (last_message.tool_calls or [])]

        # Check each requested tool against the allowlist
        blocked = [n for n in tool_names_called if n not in ALLOWED_TOOLS]
        if blocked:
            log.warning("agent.tool_node.blocked", blocked_tools=blocked)
            # Return error messages for blocked tools so the LLM can react
            error_messages = [
                ToolMessage(
                    content=f"Tool '{name}' is not available.",
                    tool_call_id=tc["id"],
                )
                for tc in (last_message.tool_calls or [])
                for name in [tc["name"]]
                if name in blocked
            ]
            return {
                "messages": error_messages,
                "tools_used": blocked,
            }

        # All tools are allowed — delegate to LangGraph's ToolNode
        result = await inner.ainvoke(state)
        return {
            "messages": result["messages"],
            "tools_used": tool_names_called,
        }

    return tool_node


# ── Node: Final synthesis (synth model) ───────────────────────────────────────
async def synthesis_node(state: AgentState, synth_llm) -> dict:
    """
    Called once after the ReAct loop completes.
    Receives the full conversation (including all tool results) and writes
    the final polished travel plan.
    """
    messages = [HumanMessage(content=SYNTHESIS_SYSTEM)] + state["messages"]

    response: AIMessage = await synth_llm.ainvoke(messages)

    usage = response.response_metadata.get("usage_metadata") or \
            response.response_metadata.get("token_usage") or {}
    new_tokens = (usage.get("total_token_count")
                  or usage.get("total_tokens")
                  or 0)

    log.info("agent.synthesis_node", tokens=new_tokens)

    return {
        "messages": [response],
        "synth_tokens": state["synth_tokens"] + new_tokens,
    }


# ── Routing logic ─────────────────────────────────────────────────────────────
def route_after_agent(state: AgentState) -> str:
    """
    Decides what happens after agent_node runs:
    - If the model produced tool calls AND we haven't hit the iteration cap → run tools
    - Otherwise → synthesis
    """
    last_message: AIMessage = state["messages"][-1] #latest response from the fast model
    has_tool_calls = bool(getattr(last_message, "tool_calls", None))
    over_limit = state["iteration"] >= MAX_ITERATIONS

    if has_tool_calls and not over_limit:
        return "tool_node"

    if over_limit and has_tool_calls:
        log.warning("agent.max_iterations_reached", iteration=state["iteration"])

    return "synthesis_node"


# ── Graph factory ─────────────────────────────────────────────────────────────
def build_graph(session: AsyncSession):
    """
    Builds and compiles the LangGraph agent.
    Called once per request — the session is captured in the RAG tool closure.

    Returns a compiled LangGraph runnable ready for .astream_events().
    """
    settings = get_settings()

    if settings.llm_provider == "groq":
        from langchain_groq import ChatGroq
        fast_llm = ChatGroq(
            model=settings.fast_model,
            groq_api_key=settings.groq_api_key,
            temperature=0,
            request_timeout=30,
        )
        synth_llm = ChatGroq(
            model=settings.synth_model,
            groq_api_key=settings.groq_api_key,
            temperature=0.4,
            request_timeout=45,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        fast_llm = ChatGoogleGenerativeAI(
            model=settings.fast_model,
            google_api_key=settings.google_api_key,
            temperature=0,
            timeout=30,
        )
        synth_llm = ChatGoogleGenerativeAI(
            model=settings.synth_model,
            google_api_key=settings.google_api_key,
            temperature=0.4,
            timeout=45,
        )

    # All tools come from the registry — session injected into RAG tool here
    tools = build_tools(session)
    fast_llm_with_tools = fast_llm.bind_tools(tools)

    # Wrap nodes with their dependencies using lambdas
    # (LangGraph nodes receive only `state` — dependencies go in closures)
    async def _agent_node(state: AgentState): #LangGraph only knows how to call a node with one argument: state
        return await agent_node(state, fast_llm_with_tools) ## we secretly pass the LLM too

    async def _synthesis_node(state: AgentState):
        return await synthesis_node(state, synth_llm)

    _tool_node = make_tool_node(tools)

    # ── Assemble graph ────────────────────────────────────────────────────────
    graph = StateGraph(AgentState) #build graph

    #add nodes
    graph.add_node("agent_node", _agent_node)
    graph.add_node("tool_node", _tool_node)
    graph.add_node("synthesis_node", _synthesis_node)

    graph.add_edge(START, "agent_node")

    # After agent_node: either loop through tools or go to synthesis
    graph.add_conditional_edges(
        "agent_node",
        route_after_agent,
        {"tool_node": "tool_node", "synthesis_node": "synthesis_node"},
    )

    # After tools run: always go back to agent_node to decide next step
    graph.add_edge("tool_node", "agent_node")

    # Synthesis is always the final step
    graph.add_edge("synthesis_node", END)

    return graph.compile()
