from sda.streamlit.functions import db_utils as database
import streamlit as st

st.title(":material/analytics: Process 1")
st.divider()

# Database status and loading
database.status()