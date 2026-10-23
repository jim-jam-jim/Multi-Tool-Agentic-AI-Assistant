# import streamlit as st
# from langgraph_backend import chatbot
# from langchain_core.messages import HumanMessage
# import uuid


# # ----------------- Utility Functions--------------------------

# def generate_thread_id():
#     thread_id = uuid.uuid4()
#     return thread_id


# def reset_chat():
#     thread_id= generate_thread_id()
#     st.session_state['thread_id']=thread_id
#     add_thread(st.session_state['thread_id'])
#     st.session_state['message_history']=[]


# def add_thread(thread_id):
#    if thread_id not in st.session_state['chat_threads']:
#        st.session_state['chat_threads'].append(thread_id)

# def load_conversation(thread_id):
#     state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
#     # Check if messages key exists in state values, return empty list if not
#     return state.values.get('messages', [])

# # ------------------session setup-----------------------

# if 'message_history' not in st.session_state:
#     st.session_state['message_history'] = []

# if 'thread_id' not in st.session_state:
#     st.session_state['thread_id']=generate_thread_id()

# if 'chat_threads' not in st.session_state:
#     st.session_state['chat_threads']=[]

# add_thread(st.session_state['thread_id'])

# #---------------------- SIde BaR UI -------------------------

# st.sidebar.title('LangGraph Chatbot')
# if st.sidebar.button('New Chat'):
#     reset_chat()

# st.sidebar.header('My conversations')

# for thread_id in st.session_state['chat_threads'][::-1]:
#     if st.sidebar.button(str(thread_id)):
#         st.session_state['thread_id'] = thread_id
#         messages = load_conversation(thread_id)

#         temp_messages = []

#         for msg in messages:
#             if isinstance(msg, HumanMessage):
#                 role='user'
#             else:
#                 role='assistant'
#             temp_messages.append({'role': role, 'content': msg.content})

#         st.session_state['message_history'] = temp_messages


# # --------------------------- Main UI------------------------------

# # loading the conversation history
# for message in st.session_state['message_history']:
#     with st.chat_message(message['role']):
#         st.text(message['content'])


# #{'role': 'user', 'content': 'Hi'}
# #{'role': 'assistant', 'content': 'Hi=ello'}

# user_input = st.chat_input('Type here')

# if user_input:

#     # first add the message to message_history
#     st.session_state['message_history'].append({'role': 'user', 'content': user_input})
#     with st.chat_message('user'):  # displays the  use message immediately
#         st.text(user_input)


#     CONFIG = { 'configurable': { 'thread_id': st.session_state['thread_id']}}

#     # first add the message to message_history
#     with st.chat_message('assistant'):

#         ai_message = st.write_stream(
#             message_chunk.content for message_chunk, metadata in chatbot.stream(
#                 {'messages': [HumanMessage(content=user_input)]},
#                 config= CONFIG,
#                 stream_mode= 'messages'
#             )
#         )

#     st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})


import streamlit as st
from langgraph_tool_backend import chatbot
from langchain_core.messages import HumanMessage
import uuid


# ============================================================
# Utility Functions
# ============================================================

def generate_thread_id():
    return str(uuid.uuid4())


def reset_chat():

    # Create a new thread
    thread_id = generate_thread_id()

    st.session_state['thread_id'] = thread_id

    # Start with empty conversation
    st.session_state['message_history'] = []


def add_thread(thread_id):

    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)


def load_conversation(thread_id):

    state = chatbot.get_state(
        config={
            'configurable': {
                'thread_id': thread_id
            }
        }
    )

    return state.values.get('messages', [])


# ============================================================
# Session State Setup
# ============================================================

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []


if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()


if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []


# ============================================================
# Sidebar UI
# ============================================================

st.sidebar.title("LangGraph Chatbot")


# New Chat
if st.sidebar.button("New Chat", use_container_width=True):

    reset_chat()

    st.rerun()


# Chats heading
st.sidebar.markdown("### Chats")

st.sidebar.markdown("---")


# ============================================================
# Display Conversations
# ============================================================

for thread_id in st.session_state['chat_threads'][::-1]:

    # Load messages from LangGraph
    messages = load_conversation(thread_id)

    # --------------------------------------------------------
    # Skip empty conversations
    # --------------------------------------------------------

    if not messages:
        continue


    # --------------------------------------------------------
    # Get conversation title
    # --------------------------------------------------------

    title = "New conversation"

    for msg in messages:

        if isinstance(msg, HumanMessage):

            title = msg.content[:30]

            if len(msg.content) > 30:
                title += "..."

            break


    # --------------------------------------------------------
    # Display conversation
    # --------------------------------------------------------

    if st.sidebar.button(
        title,
        key=f"thread_{thread_id}",
        use_container_width=True
    ):

        # Change active thread
        st.session_state['thread_id'] = thread_id


        # Load messages
        temp_messages = []

        for msg in messages:

            if isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"

            temp_messages.append({
                "role": role,
                "content": msg.content
            })


        st.session_state['message_history'] = temp_messages

        st.rerun()


# ============================================================
# Main Chat UI
# ============================================================

for message in st.session_state['message_history']:

    with st.chat_message(message['role']):

        st.markdown(message['content'])


# ============================================================
# User Input
# ============================================================

user_input = st.chat_input("Type here")


if user_input:

    # --------------------------------------------------------
    # IMPORTANT:
    # Add thread ONLY when user actually sends a message
    # --------------------------------------------------------

    add_thread(st.session_state['thread_id'])


    # --------------------------------------------------------
    # Add user message to UI history
    # --------------------------------------------------------

    st.session_state['message_history'].append({
        'role': 'user',
        'content': user_input
    })


    # --------------------------------------------------------
    # Display user message
    # --------------------------------------------------------

    with st.chat_message('user'):

        st.markdown(user_input)


    # --------------------------------------------------------
    # LangGraph configuration
    # --------------------------------------------------------

    CONFIG = {
        'configurable': {
            'thread_id': st.session_state['thread_id']
        }
    }


    # --------------------------------------------------------
    # Generate AI response
    # --------------------------------------------------------

    with st.chat_message('assistant'):

        ai_message = st.write_stream(

            message_chunk.content

            for message_chunk, metadata in chatbot.stream(

                {
                    'messages': [
                        HumanMessage(content=user_input)
                    ]
                },

                config=CONFIG,

                stream_mode='messages'
            )
        )


    # --------------------------------------------------------
    # Save AI response
    # --------------------------------------------------------

    st.session_state['message_history'].append({
        'role': 'assistant',
        'content': ai_message
    })