import streamlit as st

st.title("HELLO STREAMLIT")

st.write("If you can see this, Streamlit is working.")

name = st.text_input("Enter your name")

if name:
    st.success(f"Hello {name}")