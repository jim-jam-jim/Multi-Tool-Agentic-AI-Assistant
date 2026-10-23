import streamlit as st
from claude_langgraph_mcp_backend import chatbot, retrieve_all_threads, sync_stream
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid


# ============================================================
# Utility Functions
# ============================================================

def generate_thread_id():
    return str(uuid.uuid4())


def reset_chat():
    """
    Creates a new empty conversation.
    """

    st.session_state["thread_id"] = generate_thread_id()

    st.session_state["message_history"] = []


def add_thread(thread_id):
    """
    Adds thread to the current session's thread list.
    """

    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def to_text(content):
    """
    Groq/LangChain message content can be a string or a list of content blocks.
    Always hand a plain string to st.markdown.
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:

            if isinstance(block, str):
                parts.append(block)

            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))

        return "".join(parts)

    return ""


def load_conversation(thread_id):
    """
    Loads messages stored by LangGraph for a thread.
    """

    state = chatbot.get_state(
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    return state.values.get("messages", [])


def get_thread_title(thread_id):
    """
    Gets the first user message and uses it as
    the conversation title.
    """

    messages = load_conversation(thread_id)

    for message in messages:

        if isinstance(message, HumanMessage):

            title = to_text(message.content).strip()

            if not title:
                continue

            if len(title) > 30:
                title = title[:30] + "..."

            return title, messages

    return None, messages


# ============================================================
# Session State
# ============================================================

if "message_history" not in st.session_state:

    st.session_state["message_history"] = []


if "thread_id" not in st.session_state:

    st.session_state["thread_id"] = generate_thread_id()


if "chat_threads" not in st.session_state:

    st.session_state["chat_threads"] = retrieve_all_threads()


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("LangGraph Chatbot")


# ------------------------------------------------------------
# New Chat
# ------------------------------------------------------------

if st.sidebar.button(
    "New Chat",
    use_container_width=True
):

    reset_chat()

    st.rerun()


# ------------------------------------------------------------
# Chats
# ------------------------------------------------------------

st.sidebar.markdown("### Chats")

st.sidebar.markdown("---")


# ------------------------------------------------------------
# Display existing conversations
# ------------------------------------------------------------

for thread_id in reversed(st.session_state["chat_threads"]):

    try:

        title, messages = get_thread_title(thread_id)

    except Exception:

        continue


    # Don't display empty threads

    if not messages:
        continue


    if title is None:
        continue


    # --------------------------------------------------------
    # Conversation button
    # --------------------------------------------------------

    if st.sidebar.button(
        title,
        key=f"thread_{thread_id}",
        use_container_width=True
    ):

        # Change active thread

        st.session_state["thread_id"] = thread_id


        # Load conversation into UI

        temp_messages = []

        for message in messages:

            # Tool results are internal, don't render them as chat bubbles

            if isinstance(message, ToolMessage):
                continue


            content = to_text(message.content)

            if not content.strip():
                continue


            if isinstance(message, HumanMessage):

                role = "user"

            else:

                role = "assistant"


            temp_messages.append(
                {
                    "role": role,
                    "content": content
                }
            )


        st.session_state["message_history"] = temp_messages

        st.rerun()


# ============================================================
# Main Chat Area ( main ui)
# ============================================================

# render history
for message in st.session_state["message_history"]:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# Chat Input
# ============================================================

user_input = st.chat_input("Type here")


if user_input:

    # --------------------------------------------------------
    # Add current thread to thread list
    # --------------------------------------------------------

    add_thread(
        st.session_state["thread_id"]
    )


    # --------------------------------------------------------
    # User message
    # --------------------------------------------------------

    st.session_state["message_history"].append(
        {
            "role": "user",
            "content": user_input
        }
    )


    with st.chat_message("user"):

        st.markdown(user_input)


    # --------------------------------------------------------
    # LangGraph configuration
    # --------------------------------------------------------

    CONFIG = {
        "configurable": {
            "thread_id": st.session_state["thread_id"]
        },
        "metadata": {
            "thread_id": st.session_state["thread_id"]
        },
        "run_name": "chat_turn",
    }


    # --------------------------------------------------------
    # AI response
    # --------------------------------------------------------

    async def ai_only_stream():
        """
        Runs on the backend event loop. Yields tagged events so that all
        Streamlit calls stay on the main thread.
        """

        async for message_chunk, metadata in chatbot.astream(
            {
                "messages": [
                    HumanMessage(content=user_input)
                ]
            },
            config=CONFIG,
            stream_mode="messages",
        ):

            # -------------------------------
            # Tool execution
            # -------------------------------

            if isinstance(message_chunk, ToolMessage):

                yield ("tool", getattr(message_chunk, "name", "tool"))


            # -------------------------------
            # Assistant tokens
            # -------------------------------

            elif isinstance(message_chunk, AIMessage):

                content = message_chunk.content

                if isinstance(content, str) and content:
                    yield ("text", content)


    def render_stream():
        """
        Consumed by st.write_stream on the main thread: updates the tool
        status box and yields only the assistant text.
        """

        status_holder = {"box": None}

        for kind, payload in sync_stream(ai_only_stream()):

            if kind == "tool":

                if status_holder["box"] is None:

                    status_holder["box"] = st.status(
                        f"🔧 Using `{payload}` …",
                        expanded=True
                    )

                else:

                    status_holder["box"].update(
                        label=f"🔧 Using `{payload}` …",
                        state="running",
                        expanded=True
                    )

            else:

                yield payload


        # -------------------------------
        # Finish tool status
        # -------------------------------

        if status_holder["box"] is not None:

            status_holder["box"].update(
                label="✅ Tool finished",
                state="complete",
                expanded=False
            )


    # Assistant streaming block

    with st.chat_message("assistant"):

        ai_message = st.write_stream(
            render_stream()
        )


    # --------------------------------------------------------
    # Save response in Streamlit history
    # --------------------------------------------------------

    st.session_state["message_history"].append(
        {
            "role": "assistant",
            "content": ai_message
        }
    )
