############# Page Header #############
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import pages, session
import streamlit as st

st.title(":material/instant_mix: Manage Pages")
st.divider()

database.status()

if database.is_loaded():
    
    # Manage Custom Pages
    col_layout = [0.05, 0.3, 0.3, 0.3]

    row_header= st.columns(col_layout)
    row_header[1].container().subheader(":material/web: Page Name")
    row_header[2].container().subheader(":material/settings_b_roll: Actions")

    # List of Custom Pages
    page_list = pages.get_pages()

    for ii, page_id in enumerate(page_list):
        page_content = pages.get_page_content(page_id)
        page_name = page_content["page_settings"]["title"]
        page_icon = page_content["page_settings"]["icon"]
        page_folder = page_content["page_settings"]["file"]
        row_page = st.columns(col_layout)

        ####### Session ID
        tile = row_page[0].container()
        if page_content["page_settings"]["visible"]:
            icon = ":material/visibility:"
        else:
            icon = ":material/visibility_off:"
        tile.button(icon,
                    use_container_width = False,
                    key = f"page_{page_id}_hide",
                    on_click = pages.visibility,
                    args = [page_id]) 

        ####### Session Name
        tile = row_page[1].container()
        if page_content["page_settings"]["visible"]:
            tile.success(f"**{page_icon} {page_name}**")
        else:
            tile.info(f"**{page_icon} {page_name}**")

        ####### Actions
        tile = row_page[2].container()

        sub_row_page = tile.columns([0.1, 0.1, 0.1, 0.3, 0.2])
        
        ##
        sub_tile = sub_row_page[0].container()
        disabled = not page_content["page_settings"]["removable"]
        sub_tile.button(":material/edit:",
                        use_container_width = True,
                        key = f"page_{page_id}_edit",
                        on_click = pages.edit_settings,
                        args = [page_id],
                        disabled = disabled)
        
        ##
        sub_tile = sub_row_page[1].container()
        disabled = True if ii == 0 else False
        sub_tile.button(":material/arrow_upward:",
                        use_container_width = True,
                        key = f"page_{page_id}_moveup",
                        on_click = pages.change_order,
                        args = [page_id, "UP"],
                        disabled = disabled)
        
        ##
        sub_tile = sub_row_page[2].container()
        disabled = True if ii == len(page_list)-1 else False
        sub_tile.button(":material/arrow_downward:",
                        use_container_width = True,
                        key = f"page_{page_id}_movedown",
                        on_click = pages.change_order,
                        args = [page_id, "DOWN"],
                        disabled = disabled)

        ##
        sub_tile = sub_row_page[3].container()
        disabled = not page_content["page_settings"]["removable"]
        sub_tile.button(":material/refresh: Clean Page",
                        use_container_width = True,
                        key = f"page_{page_id}_clean",
                        on_click = pages.clean_check,
                        args = [page_id],
                        disabled = disabled)

        ##
        sub_tile = sub_row_page[4].container()
        disabled = not page_content["page_settings"]["removable"]
        sub_tile.button(":material/delete:",
                        key = f"page_{page_id}_remove",
                        type = "primary",
                        on_click = pages.remove_check,
                        args = [page_id],
                        disabled = disabled)

    # Create New Custom Page
    row_create = st.columns(col_layout)
    create_tile = row_create[1].container()
    new_page_name = create_tile.text_input(":material/add_ad: Create Page", label_visibility="collapsed")
    create_button = row_create[2].container().button(":material/add_ad: Create Page")

    if create_button:
        pages.create(new_page_name)

    if session.is_dev_mode():
        st.divider()
        st.write(st.session_state["session"]["content"]["pages"])