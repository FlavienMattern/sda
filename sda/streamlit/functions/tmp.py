import streamlit as st

def set(name, variable):
    st.session_state["tmp"][name] = variable

def get(name):
    variable = st.session_state.get("tmp")[name]
    # st.session_state["tmp"].pop(name)
    return variable