import streamlit as st
import uuid
from sda.streamlit.functions import session, modules, tmp


def generate_unique_id():
    return str(uuid.uuid4())


class Page:

    def __init__(self, title, visible=True, removable=True, default_page=False, init_tabs=True):

        self.show_block = False

        if st.session_state.get("session")["content"] is None:
            st.session_state["session"]["content"] = {}

        if "pages" not in st.session_state.get("session")["content"].keys():
            st.session_state["session"]["content"]["pages"] = {}

        # Check if page is already stored
        id_exists = False
        for page_id in st.session_state["session"]["content"]["pages"].keys():
            if title == st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["title"]:
                self.page_id = page_id
                id_exists = True
                break

        if not id_exists:
            self.page_id = self.create_page(title, visible=visible, removable=removable, default_page=default_page)
        else:
            st.session_state["session"]["content"]["pages"][page_id]["page_settings"] = {
                "title": title,
                "visible": visible,
                "removable": removable,
                "default_page": default_page,
            }
            
        if not default_page:
            if "custom_layout" not in st.session_state["session"]["content"]["pages"][page_id].keys():
                st.session_state["session"]["content"]["pages"][page_id]["custom_layout"] = {}


        if title != ":material/dashboard: Dashboard":
            st.title(title)
            st.divider()
            
        st.write(st.session_state["session"]["content"]["pages"])

        # if init_tabs:
        #     tab_list = self.get_tabs() + [":material/add_circle:"]
        #     tabs = st.tabs(tab_list)

        #     for itab, tab_id in enumerate(tab_list[:-1]):

        #         tab = tabs[itab]

        #         with tab:
        #             row_header = st.columns(2)
        #             tile_options = row_header[0].container()

        #             if tile_options.toggle("Edition mode", key=f"{tab_id}_edition", value=False):
        #                 render_mode = "edition"
        #             else:
        #                 render_mode = "view"

        #             if session.is_dev_mode():
        #                 tile_options = row_header[1].container()
        #                 if tile_options.toggle("[DEV] Show raw blocks", key=f"{tab_id}_show_blocks", value=True):
        #                     self.show_block = True
        #                 else:
        #                     self.show_block = False

        #             t = self.get_tab(tab_id)
        #             tab_data = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][t.tab_id]
        #             tab_data["layout"] = [row for row in tab_data["layout"] if row]

        #             # Affichage des lignes de blocs racine
        #             for row_idx, row in enumerate(tab_data["layout"]):
        #                 if not row:
        #                     continue  # ignore les lignes vides

        #                 cols = st.columns(len(row))
        #                 for col_idx, blk in enumerate(row):
        #                     with cols[col_idx]:
        #                         self.render_block(blk, row, col_idx, f"{tab_id}_row{row_idx}_col{col_idx}", render_mode, tab_id)

        #             # Bouton pour ajouter une nouvelle ligne contenant un seul bloc
        #             if render_mode == "edition":
        #                 if st.button(":material/arrow_downward:", key=f"{tab_id}_new_line", use_container_width=True):
        #                     new_id = generate_unique_id()
        #                     tab_data["layout"].append([{"id": new_id, "module": None, "sub_blocks": []}])
        #                     st.rerun()

        #     tab = tabs[-1]
        #     if tab.button(":material/add: Add a new tab", key=f"{tab_id}_add_tab", use_container_width=False):
        #         self.create_tab()

        # if session.is_dev_mode():
        #     st.write(st.session_state["session"]["content"]["pages"][self.page_id])
        
    def create_page(self, title, visible=True, removable=True, default_page=False):
        # Define page id (if not found previously)
        ids = st.session_state["session"]["content"]["pages"].keys()
        existing_ids = {int(id_.split('_')[1]) for id_ in ids if id_.startswith('page_')}
        i = 0
        while i in existing_ids:
            i += 1
        page_id = f"page_{i:03d}"

        default_settings = {
            "show_title": True,
            "show_border": True,
            "height": 400,
        }

        st.session_state["session"]["content"]["pages"][page_id] = {
            "page_settings": {
                "title": title,
                "visible": visible,
                "removable": removable,
                "default_page": default_page,
            },
            "modules": {}
            
        }

        return page_id