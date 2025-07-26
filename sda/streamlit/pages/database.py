page_title = ":material/database: Database Explorer"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import page
import streamlit as st

database.status()

if database.is_loaded():
    
    # Load page
    p = page.Page(page_title, visible=True, removable=False, default_page=True)

    # Page Content    
    row = st.columns(3)

    #### Container 1 - Number of files
    tile = row[0].container()
    tile.title(":material/stacks: Number of files")
    tile.info(f"**{st.session_state.get('database')['settings']['nfiles']} files** in the database.")
    ####################################

    #### Container 2 - Number of files
    tile = row[1].container()
    tile.title(":material_folder_zip: Database Size")
    tile.info(f"**{st.session_state.get('database')['settings']['filesize_str']}**")
    ####################################

    db_content = st.session_state.get("database")["content"]
    keys = list(db_content.keys())
    keys.remove("sqlite_sequence")

    tabs = st.tabs(keys)

    for idx, tab in enumerate(tabs):
        placeholder = st.empty()
        placeholder.info("Loading database...")
        df = db_content[keys[idx]]
        if "ID" in df.columns: df.set_index("ID", inplace=True)
        tab.dataframe(df, use_container_width=True, height=800)
        placeholder.empty()