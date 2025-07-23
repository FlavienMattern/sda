from sda.streamlit.functions import db_utils as database
import streamlit as st

st.title(":material/database: Database Explorer")
st.divider()

# Database status and loading
database.status()

if st.session_state.get("db_loaded") is True:

    

    # df = st.session_state.get("db_dataframe")
    # st.dataframe(df, use_container_width=True)

    db_content = st.session_state.get("db_content")
    keys = list(db_content.keys())
    keys.remove("sqlite_sequence")

    tabs = st.tabs(keys)

    for idx, tab in enumerate(tabs):
        placeholder = st.empty()
        placeholder.info("Loading database...")
        tab.dataframe(db_content[keys[idx]], use_container_width=True)
        placeholder.empty()