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
            if title == st.session_state["session"]["content"]["pages"][page_id]["title"]:
                self.page_id = page_id
                id_exists = True
                break

        if not id_exists:
            self.page_id = self.create_page(title, visible=True, removable=True, default_page=False)
        
        st.write(st.session_state["session"]["content"]["pages"][self.page_id])

        if title != ":material/dashboard: Dashboard":
            st.title(title)
            st.divider()

        if init_tabs:
            tab_list = self.get_tabs() + [":material/add_circle:"]
            tabs = st.tabs(tab_list)

            for itab, tab_id in enumerate(tab_list[:-1]):

                tab = tabs[itab]

                with tab:
                    row_header = st.columns(2)
                    tile_options = row_header[0].container()

                    if tile_options.toggle("Edition mode", key=f"{tab_id}_edition", value=False):
                        render_mode = "edition"
                    else:
                        render_mode = "view"

                    if session.is_dev_mode():
                        tile_options = row_header[1].container()
                        if tile_options.toggle("[DEV] Show raw blocks", key=f"{tab_id}_show_blocks", value=True):
                            self.show_block = True
                        else:
                            self.show_block = False

                    t = self.get_tab(tab_id)
                    tab_data = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][t.tab_id]
                    tab_data["layout"] = [row for row in tab_data["layout"] if row]

                    # Affichage des lignes de blocs racine
                    for row_idx, row in enumerate(tab_data["layout"]):
                        if not row:
                            continue  # ignore les lignes vides

                        cols = st.columns(len(row))
                        for col_idx, blk in enumerate(row):
                            with cols[col_idx]:
                                self.render_block(blk, row, col_idx, f"{tab_id}_row{row_idx}_col{col_idx}", render_mode, tab_id)

                    # Bouton pour ajouter une nouvelle ligne contenant un seul bloc
                    if render_mode == "edition":
                        if st.button(":material/arrow_downward:", key=f"{tab_id}_new_line", use_container_width=True):
                            new_id = generate_unique_id()
                            tab_data["layout"].append([{"id": new_id, "module": None, "sub_blocks": []}])
                            st.rerun()

            tab = tabs[-1]
            if tab.button(":material/add: Add a new tab", key=f"{tab_id}_add_tab", use_container_width=False):
                self.create_tab()

        if session.is_dev_mode():
            st.write(st.session_state["session"]["content"]["pages"][self.page_id])


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
            "title": title,
            "visible": visible,
            "removable": removable,
            "default_page": default_page,
            "tabs": {
                "tab_000": {
                    "name": "Tab 1",
                    "layout": [[{"id": "block_1", "settings":default_settings, "module":None, "sub_blocks": []}]]
                }
            }
        }

        return page_id



    def create_tab(self):
        ids = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"].keys()

        existing_ids = {int(id_.split('_')[1]) for id_ in ids if id_.startswith('tab_')}
        i = 0
        while i in existing_ids:
            i += 1
        tab_id = f"tab_{i:03d}"

        st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][tab_id] = {
            "name": f"Tab {i}",
            "layout": [[{"id": "block_1", "tabs":[], "module":None, "sub_blocks": []}]]
        }

        st.rerun()

    @st.dialog("Block Settings")
    def show_block_settings(self):

        st.divider()
        
        st.selectbox("Paramètres à changer", ["Valeur 1", "Valeur 2", "Valeur 3"], key="1")
        st.selectbox("Paramètres à changer", ["Valeur 1", "Valeur 2", "Valeur 3"], key="2")
        st.selectbox("Paramètres à changer", ["Valeur 1", "Valeur 2", "Valeur 3"], key="3")
        st.selectbox("Paramètres à changer", ["Valeur 1", "Valeur 2", "Valeur 3"], key="4")

        st.divider()

        if st.button("Ok", key="submit_settings", use_container_width=True):
            pass



    def render_block(self, block, parent_blocks, idx, key_prefix, render_mode, tab_id):

        module_list = ["No module selected"] + list(modules.list().keys())

        with st.container(border=True):
            if render_mode == "edition":
                # Block Header
                row = st.columns([0.1, 0.9, 0.1])
                
                # Settings block
                tile = row[0].container()
                if tile.button(":material/discover_tune:", key=f"{key_prefix}_block_settings", use_container_width=True):
                    self.show_block_settings()

                tile = row[1].container()
                # Check if a module exists for the block
                layout = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][tab_id]["layout"]
                module_block = self.get_module(layout, block['id'])
                # module_block.pop("sub_blocks")

                module_name = self.get_module_name(module_block)
                if module_name in module_list:
                    idx_select = module_list.index(module_name)
                else:
                    idx_select = 0

                if session.is_dev_mode():
                    vis = "visible"
                else:
                    vis = "collapsed"
                select_modname = tile.selectbox(block['id'], module_list, index=idx_select, key=f"{key_prefix}_selectmodule", label_visibility=vis)

                if select_modname != "No module selected":
                    self.set_module(tab_id, block['id'], select_modname, render_mode)
                elif select_modname == "No module selected":
                    self.set_module(tab_id, block['id'], None, render_mode)
    

                # Delete current block
                tile = row[2].container()
                if block["id"] == "block_1":
                    tile.button(":material/delete:", key=f"{key_prefix}_delete", type="primary", disabled=True, use_container_width=True)
                else:
                    if tile.button(":material/delete:", key=f"{key_prefix}_delete", type="primary", use_container_width=True):
                        parent_blocks.pop(idx)
                        st.rerun()
                        
                _, col_add_line, col_add_right = st.columns([0.1, 0.9, 0.1])

                
                # Ajouter une nouvelle ligne avec un seul bloc dans sub_blocks
                if col_add_line.button(":material/library_add:", key=f"{key_prefix}_add_row", use_container_width=True):
                    new_id = generate_unique_id()
                    block["sub_blocks"].append([{"id": new_id, "module":None, "sub_blocks": []}])
                    st.rerun()

                # Ajouter un bloc à droite dans la ligne actuelle
                if col_add_right.button(":material/arrow_forward:", key=f"{key_prefix}_add_right", use_container_width=True):
                    new_id = generate_unique_id()
                    parent_blocks.insert(idx+1, {"id": new_id, "module":None, "sub_blocks": []})
                    st.rerun()


                # Assurer la bonne structure de sub_blocks : liste de lignes
                if "sub_blocks" not in block or not isinstance(block["sub_blocks"], list):
                    block["sub_blocks"] = []
                if block["sub_blocks"] and isinstance(block["sub_blocks"][0], dict):
                    # Ancien format : convertir en une seule ligne
                    block["sub_blocks"] = [block["sub_blocks"]]


                if session.is_dev_mode() and self.show_block:
                    layout = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][tab_id]["layout"]
                    module_block = self.get_module(layout, block['id'])
                    st.write({k: module_block[k] for k in ["id","module"] if k in module_block})

            else:

                # Check if a module exists for the block
                layout = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][tab_id]["layout"]
                module_block = self.get_module(layout, block['id'])
                # module_block.pop("sub_blocks")
                if session.is_dev_mode() and self.show_block:
                    st.write({k: module_block[k] for k in ["id","module"] if k in module_block})
                module_name = self.get_module_name(module_block)
                self.set_module(tab_id, block['id'], module_name, render_mode)

                if session.is_dev_mode() and self.show_block:
                    layout = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][tab_id]["layout"]
                    module_block = self.get_module(layout, block['id'])
                    st.write({k: module_block[k] for k in ["id","module","tabs"] if k in module_block})


            # Affichage des lignes de sous-blocs
            for row_idx, row in enumerate(block["sub_blocks"]):
                if not row:
                    continue

                cols = st.columns(len(row))
                for col_idx, sub_block in enumerate(row):
                    with cols[col_idx]:
                        self.render_block(sub_block, row, col_idx, f"{key_prefix}_r{row_idx}_c{col_idx}", render_mode, tab_id)
                        module_name = self.get_module_name(sub_block)
                        self.set_module(tab_id, sub_block['id'], module_name, render_mode)



    def set_module(self, tab_id, block_id, module_id, render_mode):

        layout = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"][tab_id]["layout"]

        if module_id is None:
            block = self.get_module(layout, block_id)
            block["module"] = None
            
        else:
            module_name = modules.list()[module_id]
            for row in layout:
                for block in row:
                    if block.get("id") == block_id:
                        block["module"] = {"id":module_id, "name":module_name, "settings":{}}
                    # Recherche récursive dans les sub_blocks
                    sub_layout = block.get("sub_blocks", [])
                    if sub_layout:
                        result = self.get_module(sub_layout, block_id)
                        if result:
                            result["module"] = {"id": module_id, "name": module_name, "settings": {}}

            if render_mode == "view":
                modules.dataframe_stations(tmp.get("stations_inventory"))



    def get_module_name(self, module_block):
        if module_block["module"] is None:
            return None
        else:
            return module_block["module"]["id"]



    def get_module(self, layout, block_id):
        for row in layout:
            for block in row:
                if block.get("id") == block_id:
                    return block
                # Recherche récursive dans les sub_blocks
                sub_layout = block.get("sub_blocks", [])
                if sub_layout:
                    result = self.get_module(sub_layout, block_id)
                    if result:
                        return result
        return None



    def get_tabs(self):
        # tabs = st.session_state["session"]["content"]["pages"][self.page_id]["tabs"]
        # return [tabs[key]["name"] for key in tabs]
        return list(st.session_state["session"]["content"]["pages"][self.page_id]["tabs"].keys())

    def get_tab(self, tab_id):
        return Tab(self.page_id, tab_id)

    def get_content(self):
        return st.session_state["session"]["content"]["pages"][self.page_id]

    def get_title(self):
        return st.session_state["session"]["content"]["pages"][self.page_id]["title"]

    def is_removable(self):
        return st.session_state["session"]["content"]["pages"][self.page_id]["removable"]

    def is_visible(self):
        return st.session_state["session"]["content"]["pages"][self.page_id]["visible"]

    def is_default_page(self):
        return st.session_state["session"]["content"]["pages"][self.page_id]["default_page"]




class Tab:

    def __init__(self, page_id, tab_id):
        self.page_id = page_id
        self.tab_id = tab_id

    def get_content(self):
        return st.session_state["session"]["content"]["pages"][self.page_id][self.tab_id]