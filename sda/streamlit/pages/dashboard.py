import streamlit as st
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import session
import pandas as pd

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


#### Container 2 - Session Status
if database.is_loaded():
    tile = row[1].container()
    tile.title(":material/web: Current Session")

    tile.info(f"Session loaded : **{st.session_state.get('session')['settings']['name']}**")

    #### Manage sessions
    st.divider()
    st.title(":material/settings_b_roll: Manage sessions")
    col_layout = [0.15, 0.2, 0.2, 0.3, 0.15]

    row_header= st.columns(col_layout)
    row_header[1].container().subheader(":material/web: Session Name")
    row_header[2].container().subheader(":material/edit_calendar: Last Changed")
    row_header[3].container().subheader(":material/code_blocks: Actions")

    sessions = session.get_sessions_list()
    sessions["last_used"] = pd.to_datetime(sessions['last_used'], format='%Y-%m-%d %H:%M:%S')
    sessions = sessions.sort_values("last_used", ascending=False)

    for idx, row in sessions.iterrows():
        session_id = idx
        session_name = row.session_name
        session_last_used = row.last_used
        session_folder = row.session_folder

        

        if session_id == st.session_state.get("session")["settings"]["id"]:
            clean_disabled = False
            select_disabled = True
        else:
            clean_disabled = True
            select_disabled = False

        if session_id == 0:
            remove_disabled = True
        else:
            remove_disabled = False

        row_page = st.columns(col_layout)

        ####### Select Session
        tile = row_page[0].container()
        tile.button(":material/arrow_forward: Select Session",
                    key = f"{session_id:03d}_select",
                    use_container_width = True,
                    disabled = select_disabled,
                    on_click = session.load,
                    args = [idx])

        ####### Session Name
        tile = row_page[1].container()
        if select_disabled :
            tile.info(f"**{session_name}**")
        else:
            tile.warning(f"**{session_name}**")

        ####### Last Changed
        tile = row_page[2].container()
        if select_disabled :
            tile.info(session_last_used)
        else:
            tile.warning(session_last_used)

        # ####### Check Actions
        # if st.session_state.get(f"{session_id:03d}_select"):
        #     session.load(session_id)
        #     st.rerun()

        # if st.session_state.get(f"{session_id:03d}_clean"):
        #     session.clean()
        #     st.rerun()

        ####### Actions
        tile = row_page[3].container()

        sub_row_page = tile.columns(2)

        sub_tile = sub_row_page[0].container()
        sub_tile.button(":material/refresh: Clean Session",
                        use_container_width = True,
                        key = f"{session_id:03d}_clean",
                        disabled = clean_disabled,
                        on_click = session.clean_check)

        sub_tile = sub_row_page[1].container()
        sub_tile.button(":material/delete:",
                        key = f"{session_id:03d}_remove",
                        disabled = remove_disabled,
                        type = "primary",
                        on_click = session.remove_check,
                        args = [idx])


    row_create = st.columns(col_layout)
    create_tile = row_create[1].container()
    new_session_name = create_tile.text_input(":material/add_ad: Create Session", label_visibility="collapsed")
    create_button = row_create[2].container().button(":material/add_ad: Create Session")

    if create_button:
        session.create(new_session_name)
