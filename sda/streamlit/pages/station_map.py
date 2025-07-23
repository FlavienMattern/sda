from sda.streamlit.functions import db_utils as database
import streamlit as st

st.title(":material/map: Map Explorer")
st.divider()
database.status()