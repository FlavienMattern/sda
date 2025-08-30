import streamlit as st
import pandas as pd
import os
import pickle as pkl
from datetime import datetime
import shutil

def is_in_session():
    if "session" in st.session_state.keys():
        return len(st.session_state.get("session").keys()) > 0
    else:
        return False


def status_sidebar():
    if is_in_session():
        st.sidebar.info(f":material/web: Session : **{st.session_state.get('session')['settings']['name']}**")

    else:
        st.sidebar.info(":material/web: No session loaded.")


def get_sessions_list():

    try:
        sessions = pd.read_csv(os.path.join(st.session_state.get("database")["settings"]["wdir"], "streamlit", "sessions.txt"), delimiter=",")
        sessions.set_index("id", inplace=True)
        st.session_state["all_sessions"] = sessions
        return sessions
    except:
        return None


def save_sessions_list(update_current_session_date=True):

    wdir = st.session_state.get("database")["settings"]["wdir"]
    sessions = st.session_state.get("all_sessions")

    if update_current_session_date:
        session_id = st.session_state.get("session")["settings"]["id"]
        sessions.loc[session_id, 'last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sessions.loc[session_id, 'session_name'] = st.session_state.get("session")["settings"]["name"]

    sessions.to_csv(os.path.join(wdir, "streamlit", "sessions.txt"))


def load(id):

    sessions = get_sessions_list()
    session_name = sessions[sessions.index == id].session_name.values[0]
    wdir = st.session_state.get("database")["settings"]["wdir"]

    session_file = os.path.join(wdir, "streamlit", f"session_{id:03d}", "session.info")

    with open(session_file, "rb") as f:
        session_dict = pkl.load(f)

    st.session_state["session"] = session_dict


def save():
    
    wdir = st.session_state.get("database")["settings"]["wdir"]    
    st.session_state["session"]["settings"]["name"] = st.session_state.get("session")["settings"]["name"]
    session_dict = st.session_state.get("session")
    session_folder = session_dict["settings"]["folder"]

    save_folder = os.path.join(wdir, session_folder)
    save_file = os.path.join(save_folder, "session.info")

    os.makedirs(save_folder, exist_ok=True)
    with open(save_file, "wb") as f:
        pkl.dump(session_dict, f)

    save_sessions_list()


def clean():

    id = st.session_state.get("session")["settings"]["id"]

    session_dict = {
        "settings": {
            "name": st.session_state.get("session")["settings"]["name"],
            "id": id,
            "folder": f"streamlit/session_{id:03d}"
        },
        "content": None
    }

    st.session_state["session"] = session_dict

    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_dict = st.session_state.get("session")
    session_folder = session_dict["settings"]["folder"]
    rm_folder = os.path.join(wdir, session_folder)
    try:
        shutil.rmtree(rm_folder)
    except:
        pass

    save()
    st.rerun()
    
    
@st.dialog(":material/edit: Session Settings")
def edit_settings(session_id):
    with st.form(f"edit_page_{session_id}_form"):
        session_name = st.text_input("Session Name", value=st.session_state.get("session")["settings"]["name"])
        
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            if session_name in ["", None] or session_name.isspace():
                st.error(f"You need to enter a valid name !")
                return

            if session_name != st.session_state.get("session")["settings"]["name"] and session_name in get_sessions_list()["session_name"].values:
                st.error(f"A session with the name **{session_name}** already exists !")
                return
            
            st.session_state["session"]["settings"]["name"] = session_name
            
            save()
            st.rerun()


@st.dialog(":material/warning: Caution !")
def clean_check():
    session_name = st.session_state.get("session")["settings"]["name"]
    st.warning(f":material/warning: You are about to clean you current session : **{session_name}**. You will loose all information in this session. Close this popup if it was a mistake.")
    if st.button(":material/check: Clean Session"):
        clean()


def remove(id):
    sessions = get_sessions_list()
    sessions = sessions.drop(id)

    if id == st.session_state.get("session")["settings"]["id"]:
        load(0)

    wdir = st.session_state.get("database")["settings"]["wdir"]
    rm_folder = os.path.join(wdir, "streamlit", f"session_{id:03d}")
    try:
        shutil.rmtree(rm_folder)
    except:
        pass

    st.session_state["all_sessions"] = sessions
    save_sessions_list(update_current_session_date=False)
    save()
    st.rerun()


@st.dialog(":material/warning: Caution !")
def remove_check(id):
    session_name = st.session_state.get("session")["settings"]["name"]
    st.warning(f":material/warning: You are about to permanently remove the session : **{session_name}**. You will loose all information in this session. Close this popup if it was a mistake.")
    if st.button(":material/check: Remove Session"):
        remove(id)


def create(name):

    if name not in ["", " ", "  ", "Select a session"]:
            
        sessions = get_sessions_list()
        if sessions is None:
            sessions = pd.DataFrame({
                'session_name': [],
                'session_folder': [],
                'last_used': []
            })
            sessions.index.name = 'id'

        if name not in list(sessions["session_name"]):

            if len(sessions) == 0:
                id = 0
            else:
                id = max(list(sessions.index)) + 1

            session_dict = {
                "settings": {
                    "name": name,
                    "id": id,
                    "dev_mode": False,
                    "folder": f"streamlit/session_{id:03d}"
                },
                "content": None
            }

            st.session_state["session"] = session_dict

            wdir = st.session_state.get("database")["settings"]["wdir"]
            save_folder = os.path.join(wdir, "streamlit", f"session_{id:03d}")
            save_file = os.path.join(save_folder, "session.info")

            

            os.makedirs(save_folder, exist_ok=True)
            with open(save_file, "wb") as f:
                pkl.dump(session_dict, f)

            sessions.loc[id] = [name, f"session_{id:03d}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            st.session_state["all_sessions"] = sessions
            save_sessions_list()

            save()
            st.rerun()


def is_dev_mode():
    return st.session_state.get("session")["settings"]["dev_mode"]
            