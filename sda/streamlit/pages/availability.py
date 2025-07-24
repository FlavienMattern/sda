from sda.streamlit.functions import db_utils as database
import streamlit as st

st.title(":material/view_timeline: Data Availability")
st.divider()

# Database status and loading
database.status()

if database.is_loaded():
    pass