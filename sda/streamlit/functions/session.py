import streamlit as st

def is_in_session():
    a = len(st.session_state.get("session").keys()) > 0
    print(st.session_state.get("session").keys())
    return a

@st.dialog("Create a Session")
def create_session():
    st.info(f"No session loaded. Do you want to create a new session ? This name allows you to find the name of your session the next time it is loaded.")
    session_name = st.text_input("Enter a session name :")
    if st.button("Apply and save session"):
        st.session_state["session"]["settings"] = {
                "name": session_name,
                "id": 0,
                "filename": f"streamlit/{session_name}.pkl"
            }
        st.rerun()


def save():
    
    session_dict = st.session_state.get("session")
    session_name = session_dict["name"]
    session_id = session_dict["id"]
    session_filename = session_dict["filename"]
    
    st.sidebar.divider()
    
    if session_name == "No session loaded":
        create_session()
    else:
        st.sidebar.write("Saving current session")
        st.sidebar.write(f"Session Name : {session_name}")
        st.sidebar.write(f"Session ID : {session_id}")
        st.sidebar.write(f"Saved as : {session_filename}")