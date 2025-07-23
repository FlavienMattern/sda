import streamlit as st
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import session

st.title(":material/dashboard: Dashboard")
st.divider()

row = st.columns(3)

#### Container 1 - Database Status
tile = row[0].container()
tile.title(":material/database: Database Status")
if database.is_loaded():
    tile.success("✅ Database loaded.")
else:
    tile.error("❌ Database is not loaded ! Please upload a database file below.")
    
    uploaded_file = tile.file_uploader(
        "Select Database File", accept_multiple_files=False, type=["db", "sql"], label_visibility="collapsed",
    )

    database.get_db_infos(uploaded_file)
####################################

sessions_list = ["Session 1", "Session 2", "Session 3"]

#### Container 2 - Session Status
if database.is_loaded():
    tile = row[1].container()
    tile.title(":material/view_apps: Current Session")
    if session.is_in_session():
        tile.success("✅ Session loaded.")
        
        subrow = tile.columns(2)
        
        subtile = subrow[0].container()
        session_name = subtile.selectbox("Change session", options=["Select a session"] + sessions_list)
        
        st.session_state["session"] = {
            "id": session_name,
            "name": session_name,
            "filename": "stremlit/session_000.pkl",
        }    
        
        
    else:
        tile.info("No session currently loaded. You can load or create a session to save your progress.")
        
        subrow = tile.columns(2)
        
        subtile = subrow[0].container()
        session_name = subtile.selectbox("Select a session", options=["Select a session"] + sessions_list, index=0)
        
        st.session_state["session"] = {
            "id": session_name,
            "name": session_name,
            "filename": "stremlit/session_000.pkl",
        }       
        
        print("Section selected !")
        print(st.session_state["session"])


#### Container 3 - Manage Sessions
if database.is_loaded():
    tile = row[2].container()
    tile.title(":material/settings_b_roll: Manage Sessions")
    
    subrow = tile.columns(2)
    subtile = subrow[0].container()
    session_create = subtile.text_input("Enter a new session name")
    do_session_create = subtile.button(":material/add_ad: Create New Session", use_container_width=True)
    
    if do_session_create:
        
        id = 0

        st.session_state["session"]["settings"] = {
                "name": session_create,
                "id": id,
                "filename": f"streamlit/session_{id}.pkl"
            }
        
        st.session_state["tmp"]["session_created"] = True
        
        
        
    if "session_created" in st.session_state.get("tmp").keys():
        subtile.info(f"do something to create the session : {session_create}")
        st.session_state["tmp"].pop("session_created")
        
        
        
    subtile = subrow[1].container()
    session_remove = subtile.selectbox("Remove an existing session", options=sessions_list)
    do_session_remove = subtile.button(":material/delete: Remove Session", use_container_width=True)
    
    if do_session_remove:
        id = 0
        
        # do something
        
        st.session_state["tmp"]["session_removed"] = True
        st.rerun()
        
    if "session_removed" in st.session_state.get("tmp").keys():
        subtile.info(f"do something to remove the session : {session_remove}")
        st.session_state["tmp"].pop("session_removed")
        
####################################

st.divider()

st.subheader("Preferences")
a = st.selectbox("Select a preference", options=["No Preference", "Choice 1", "Choice 2", "Choice 3"])
st.session_state["dashboard_choice"] = a
st.write(f"You choose : **{a}**.")

