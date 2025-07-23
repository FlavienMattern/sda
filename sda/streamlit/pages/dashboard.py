import streamlit as st

st.title(":material/home: Dashboard")
st.divider()

row = st.columns(3)

#### Container 1 - Database Status
tile = row[0].container()
tile.title(":material/progress_activity: Database Status")
if st.session_state.get("db_loaded"):
    tile.success("✅ Database loaded.")
else:
    tile.error("❌ Database is not loaded ! Please load the database using the left sidebar.")
####################################

#### Container 2 - Number of files
if st.session_state.get("db_loaded"):
    tile = row[1].container()
    tile.title(":material/stacks: Number of files")
    tile.info(f"**{st.session_state.get('db_nfiles')} files** in the database.")
####################################

#### Container 2 - Number of files
if st.session_state.get("db_loaded"):
    tile = row[2].container()
    tile.title(":material_folder_zip: Database Size")
    tile.info(f"**{st.session_state.get('db_filesize_str')}**")
####################################