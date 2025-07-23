import streamlit as st
from sda.streamlit.functions import db_utils as database

            
# General Configuration
st.set_page_config(
    page_title="Data Viewer",
    page_icon=":material/search:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)


# Database status and loading
database.status_sidebar()
        

# Setup Navigation bar
pages = {
    "Home": [
        st.Page("pages/dashboard.py", title="Dashboard", icon=":material/home:", default=True),
    ],
    "Data Viewer": [
        st.Page("pages/database.py", title="Database Explorer", icon=":material/database:"),
        st.Page("pages/station_map.py", title="Map Explorer", icon=":material/map:"),
        st.Page("pages/process1.py", title="Process 1", icon=":material/analytics:"),
        st.Page("pages/process2.py", title="Process 2", icon=":material/browse_activity:"),
    ],
}
pg = st.navigation(pages, position="sidebar")


# Run webpage
pg.run()