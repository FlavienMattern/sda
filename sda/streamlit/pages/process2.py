from sda.streamlit.functions import db_utils as database
import streamlit as st

st.title(":material/browse_activity: Process 2")
st.divider()

# Database status and loading
database.status()