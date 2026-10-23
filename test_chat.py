import streamlit as st
from langgraph_database_backend import chatbot
from langchain_core.messages import HumanMessage

st.title("LangGraph Chatbot")

st.write("Backend imported successfully")

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = "streamlit-test"

st.write("Thread ID:", st.session_state["thread_id"])

user_input = st.chat_input("Type here")

if user_input:

    st.chat_message("user").write(user_input)

    config = {
        "configurable": {
            "thread_id": st.session_state["thread_id"]
        }
    }

    response = chatbot.invoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ]
        },
        config=config
    )

    ai_response = response["messages"][-1].content

    st.chat_message("assistant").write(ai_response)