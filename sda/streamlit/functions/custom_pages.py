import streamlit as st
import os, uuid
import numpy as np


def generate_unique_id():
    return str(uuid.uuid4())

def default_block():
    return {
            "layout": [[None,None], [None,None]],
            "widths": [[0.6,0.4], [0.4,0.6]],
            "block_id": [[generate_unique_id(),generate_unique_id()],[generate_unique_id(),generate_unique_id()]],
            "block_type": "container"
        }

container_default = {
            "layout": [[None,None],[default_block(),default_block(),None]],
            "widths": [[0.5,0.5],[0.3,0.4,0.3]],
            "block_id": [[generate_unique_id(),generate_unique_id()],[generate_unique_id(),generate_unique_id(),generate_unique_id()]],
            "block_type": "container"
        }

tab_default = {
            "layout": [[None,None]],
            "widths": [[None,None]],
            "block_id": [[generate_unique_id(),generate_unique_id()]],
            "block_type": "tab"
        }


def render_block(block):
    if block["block_type"] == "container":
        Nrows = len(block["layout"])     
        for i in range(Nrows):
            Ncols = len(block["layout"][i])
            cols = st.columns(block["widths"][i])
            for j in range(Ncols):
                sub_block = block["layout"][i][j]
                block_id = block["block_id"][i][j]
                with cols[j]:
                    # tile = cols[j].container()
                    tile = cols[j].columns([0.9, 0.1])
                    tile_content = tile[0].container()
                    tile_btn = tile[1].container()
                    
                    with tile_content.container(border=True):
                        tile2 = st.columns([0.9, 0.1])
                        tile2_select = tile2[0].container()
                        tile2_settings = tile2[1].container()
                        tile2_select.selectbox(block_id, options=[None, "Map Stations", "Dataframe Stations"], key=f"selectmodule_{block_id}", index=0)
                        tile2_settings.button(":material/dehaze:", key=f"settings_{block_id}", use_container_width=True)
                        # Dans les settings, afficher les largeurs de chaque block de la ligne pour pouvoir les modifier ensemble
                        if sub_block:
                            render_block(sub_block)
                        low_btn = st.columns([0.8, 0.2])
                        tile = low_btn[0].container()
                        tile.button(":material/add:", key=f"addrow_{block_id}", use_container_width=True)
                        tile = low_btn[1].container()
                        tile.button(":material/delete:", key=f"delete_{block_id}", type="primary", use_container_width=True)
                        
                    tile_btn.button(":material/arrow_forward:", key=f"addcol_{block_id}", use_container_width=True)
        
        
    
    

def load(page_id):
    page_content = st.session_state["session"]["content"]["pages"][page_id]
    custom_layout = page_content["custom_layout"]
    modules = page_content["modules"]
    ##############################################################
    
    if custom_layout == {}:
        custom_layout = container_default.copy()
        
    render_block(custom_layout)
    
    
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
        