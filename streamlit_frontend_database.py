import streamlit as st
from langgraph_tool_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage,ToolMessage
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

            title = message.content.strip()

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

            if isinstance(message, HumanMessage):

                role = "user"

            else:

                role = "assistant"


            temp_messages.append(
                {
                    "role": role,
                    "content": message.content
                }
            )


        st.session_state["message_history"] = temp_messages

        st.rerun()


# ============================================================
# Main Chat Area ( main ui)
# ============================================================

# render hsitory
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
    
    # show user's message
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
        "metadata":{
            "thread_id": st.session_state["thread_id"]
        },
        "run_name":"chat_turn",
    }


    # --------------------------------------------------------
    # AI response
    # --------------------------------------------------------
    # Assistant streaming block
    with st.chat_message("assistant"):
        # Use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # Lazily create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
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