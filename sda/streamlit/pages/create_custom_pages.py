############# Page Header #############
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import custom_pages as page
import streamlit as st

st.title(":material/instant_mix: Manage Pages")
st.divider()

database.status()

if database.is_loaded():
    
    # Manage Custom Pages
    col_layout = [0.1, 0.3, 0.3, 0.3]

    row_header= st.columns(col_layout)
    row_header[0].container().subheader(":material/numbers: ID")
    row_header[1].container().subheader(":material/web: Page Name")
    row_header[2].container().subheader(":material/code_blocks: Actions")

    # List of Custom Pages
    pages = page.get_pages()

    for idx, row in pages.iterrows():
        page_id = idx
        page_name = row.page_name
        page_folder = row.page_folder
        row_page = st.columns(col_layout)

        ####### Session ID
        tile = row_page[0].container()
        tile.info(f"{idx}")

        ####### Session Name
        tile = row_page[1].container()
        tile.info(f"**{page_name}**")

        ####### Actions
        tile = row_page[2].container()

        sub_row_page = tile.columns(2)

        sub_tile = sub_row_page[0].container()
        sub_tile.button(":material/refresh: Clean Page",
                        use_container_width = True,
                        key = f"page_{idx:03d}_clean",
                        on_click = page.clean_check,
                        args = [idx])

        sub_tile = sub_row_page[1].container()
        sub_tile.button(":material/delete:",
                        key = f"page_{idx:03d}_remove",
                        type = "primary",
                        on_click = page.remove_check,
                        args = [idx])

    # Create New Custom Page
    row_create = st.columns(col_layout)
    create_tile = row_create[1].container()
    new_page_name = create_tile.text_input(":material/add_ad: Create Page", label_visibility="collapsed")
    create_button = row_create[2].container().button(":material/add_ad: Create Page")

    if create_button:
        page.create(new_page_name)