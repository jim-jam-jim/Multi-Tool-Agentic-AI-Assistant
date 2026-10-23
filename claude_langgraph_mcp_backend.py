from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated

from langchain_core.messages import BaseMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool, BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
import aiosqlite
import requests
import asyncio
import threading
import queue
import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv


load_dotenv()

# ============================================================
# DEDICATED ASYNC LOOP
# ============================================================

_ASYNC_LOOP = asyncio.new_event_loop()
_LOOP_READY = threading.Event()


def _run_loop():
    asyncio.set_event_loop(_ASYNC_LOOP)
    _ASYNC_LOOP.call_soon(_LOOP_READY.set)
    _ASYNC_LOOP.run_forever()


_ASYNC_THREAD = threading.Thread(target=_run_loop, daemon=True)
_ASYNC_THREAD.start()

# Wait until the loop is actually running before anything is scheduled on it.
_LOOP_READY.wait()


def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


def run_async(coro):
    return _submit_async(coro).result()


def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)


_STREAM_DONE = object()


def sync_stream(async_gen):
    """
    Drive an async generator on the backend event loop and hand the items
    back to the calling (Streamlit) thread as a normal generator.

    This keeps every await on the same loop that owns the MCP sessions and
    the aiosqlite connection, while letting Streamlit consume it synchronously.
    """
    q: "queue.Queue" = queue.Queue()

    async def _pump():
        try:
            async for item in async_gen:
                q.put(("item", item))
        except Exception as exc:          # noqa: BLE001
            q.put(("error", exc))
        finally:
            q.put(("done", _STREAM_DONE))

    _submit_async(_pump())

    while True:
        kind, payload = q.get()
        if kind == "item":
            yield payload
        elif kind == "error":
            raise payload
        else:
            return


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)


# ============================================================
# TOOLS
# ============================================================

search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:              # noqa: BLE001
        return {"error": str(exc)}


client = MultiServerMCPClient(
    {
        "arith": {
            "transport": "stdio",
            "command": "python",
            "args": [
                r"C:\Users\Aryan Raj\Desktop\mcp-math-server\main.py"
            ],
        },
        "expense": {
            "transport": "stdio",
            "command": "python",
            "args": [r"C:\Users\Aryan Raj\Desktop\mcp-math-server\expense.py"],
},
    }
)


def load_mcp_tools() -> list[BaseTool]:
    try:
        return run_async(client.get_tools())
    except Exception as exc:              # noqa: BLE001
        print(f"[MCP] could not load tools: {exc}")
        return []


mcp_tools = load_mcp_tools()

tools = [search_tool, get_stock_price, *mcp_tools]
llm_with_tools = llm.bind_tools(tools) if tools else llm


# ============================================================
# STATE
# ============================================================

class ChatState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]


# ============================================================
# NODE
# ============================================================

EMPTY_TOOL_RESULT = "(the tool returned no output)"


def _tool_content_to_text(content) -> str:
    """Flatten whatever a tool returned into a plain string."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:

            if isinstance(block, str):
                parts.append(block)

            elif isinstance(block, dict):
                parts.append(block.get("text") or str(block))

            else:
                parts.append(str(block))

        return "\n".join(parts)

    if content is None:
        return ""

    return str(content)


def sanitize_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    Groq rejects a tool message whose content is an empty string or an
    empty list. A tool that finds nothing (an empty web search, an MCP
    call with no result) produces exactly that, and once it is written to
    the checkpoint it breaks every later turn in the thread. Replace any
    empty tool result with a short placeholder before calling the LLM.
    """

    cleaned = []

    for message in messages:

        if isinstance(message, ToolMessage):

            text = _tool_content_to_text(message.content)

            if not text.strip():
                text = EMPTY_TOOL_RESULT

            if text != message.content:
                message = message.model_copy(update={"content": text})

        cleaned.append(message)

    return cleaned


async def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""
    messages = sanitize_messages(state["messages"])
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools) if tools else None


# ============================================================
# SQLITE / CHECKPOINTER
# ============================================================

async def _init_checkpointer():
    conn = await aiosqlite.connect(database="chatbot.db")
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    return saver


checkpointer = run_async(_init_checkpointer())


# ============================================================
# GRAPH
# ============================================================

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")

if tool_node:
    graph.add_node("tools", tool_node)
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
else:
    graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)


# ============================================================
# RETRIEVE THREADS
# ============================================================

async def _alist_threads():
    all_threads = set()
    async for checkpoint in checkpointer.alist(None):
        thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
        if thread_id:
            all_threads.add(thread_id)
    return list(all_threads)


def retrieve_all_threads():
    try:
        return run_async(_alist_threads())
    except Exception as exc:              # noqa: BLE001
        print(f"[checkpointer] could not list threads: {exc}")
        return []