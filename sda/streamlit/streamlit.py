import streamlit as st
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import custom_pages as pages
from sda.streamlit.functions import session
import os

# Initiate Empty Session
if "database" not in st.session_state.keys(): st.session_state["database"] = {}
if "tmp" not in st.session_state.keys(): st.session_state["tmp"] = {}
            
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


if database.is_loaded():

    if not session.is_in_session():
        sessions = session.get_sessions_list()
        if sessions is not None:
            sessions = sessions.sort_values("last_used", ascending=False)
            session_idx = sessions.index[0]
            session_name = sessions[sessions.index == session_idx].session_name.values[0]
            session.load(session_idx)
        else:
            session.create("Default")

    session.status_sidebar()

    st.sidebar.divider()
    if st.sidebar.button(":material/save: Save Session", key = f"save_current_session"):
        session.save()

    sessions = session.get_sessions_list()
    session_idx = st.session_state.get("session")["settings"]["id"]
    last_save = sessions[sessions.index == session_idx].last_used.values[0]
    st.sidebar.caption(f"Last save : {last_save}")

    if st.sidebar.toggle("Developer Mode", key=f"dev_mode", value=False):
        st.session_state["session"]["settings"]["dev_mode"] = True
    else:
        st.session_state["session"]["settings"]["dev_mode"] = False



# Setup Navigation bar
if not session.is_dev_mode():
    nav_default_pages = {
        "Home": [
            st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        ]
    }
else:
    nav_default_pages = {
        "Home": [
            st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
            st.Page("pages/sandbox.py", title="[DEV] Sandbox", icon=":material/experiment:"),
        ]
    }
    
nav_general_pages = {
    "Data Viewer": [
        st.Page("pages/database.py", title="Database Explorer", icon=":material/database:"),
        st.Page("pages/station_map.py", title="Map Explorer", icon=":material/map:"),
        st.Page("pages/availability.py", title="Data Availability", icon=":material/view_timeline:"),
        st.Page("pages/waveforms.py", title="Waveform Viewer", icon=":material/vital_signs:"),
        st.Page("pages/process2.py", title="Process 2", icon=":material/browse_activity:"),
    ]
}

# Custom Pages
if database.is_loaded():

    custom_pages = pages.get_pages()
    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    page_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages")

    nav_custom_pages = {
        "Custom Pages": [
            st.Page("pages/create_custom_pages.py", title="Manage Custom Pages", icon=":material/instant_mix:"),
        ] + [st.Page(os.path.join(page_folder, f"page_{idx:03d}", f"layout_{idx:03d}.py"), title=row.page_name, icon=":material/add_chart:") for idx, row in custom_pages.iterrows()]
    }


# Load Navigation bar
if not database.is_loaded():
    pages = nav_default_pages | nav_general_pages
else:
    pages = nav_default_pages | nav_general_pages | nav_custom_pages
pg = st.navigation(pages, position="sidebar")
    

# Run webpage
pg.run()