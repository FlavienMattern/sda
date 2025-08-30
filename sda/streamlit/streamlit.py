import streamlit as st
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import pages
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
nav_default_pages = {
    "Home": [
        st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("pages/manage_pages.py", title="Pages", icon=":material/instant_mix:"),
    ]
}

# Default Pages
pages_dict = {
    "pages/database.py": {"title":"Database Explorer", "icon":":material/database:"},
    "pages/station_map.py": {"title":"Map Explorer", "icon":":material/map:"},
    "pages/availability.py": {"title":"Data Availability", "icon":":material/view_timeline:"},
    "pages/waveforms.py": {"title":"Waveform Viewer", "icon":":material/vital_signs:"},
    "pages/process2.py": {"title":"Process 2", "icon":":material/browse_activity:"},
}

if database.is_loaded():
   
    for key, value in pages_dict.items():
        if pages.is_visible(pages.get_page_id(key)):
            pages.Page(file=key, title=value["title"], icon=value["icon"], removable=False, default_page=True, init_tabs=False)
            
    page_list = st.session_state.get("session")["content"]["pages"]
    
    nav_general_pages = {
        "Explorer": [
            st.Page(pcontent["page_settings"]["file"], title=pcontent["page_settings"]["title"], icon=pcontent["page_settings"]["icon"])
            for pname, pcontent in page_list.items()
            if pages.is_visible(pages.get_page_id(pcontent["page_settings"]["file"]))
        ]
    }
    
    

# Load Navigation bar
if not database.is_loaded():
    page_list = nav_default_pages
else:
    page_list = nav_default_pages | nav_general_pages
pg = st.navigation(page_list, position="sidebar")
    

# Run webpage
pg.run()