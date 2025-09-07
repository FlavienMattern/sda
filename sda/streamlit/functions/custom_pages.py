import streamlit as st
from sda.streamlit.functions import modules as m
from sda.streamlit.functions import session
import uuid


def generate_unique_id():
    return str(uuid.uuid4())  # raccourci, plus lisible dans l’UI


def default_block():
    return {
        "layout": [[None]],        # une seule case vide
        "widths": [[1.0]],           # largeur 1
        "block_id": [[generate_unique_id()]],  # ID unique
        "block_type": "container"  # c’est bien un bloc de type container
    }


# def container_block():
#     return {
#         "layout": [[None]],
#         "widths": [[1]],
#         "block_id": [[generate_unique_id()]],
#         "block_type": "container"
#     }


# def tab_block():
#     return {
#         "layout": [[default_block(), default_block()]],
#         "widths": [[0.5, 0.5]],
#         "block_id": [[generate_unique_id(), generate_unique_id()]],
#         "block_type": "tab"
#     }


def add_sub_block(block, row_idx, col_idx, page_id):
    block["layout"][row_idx][col_idx] = default_block()
    block_id = block["layout"][row_idx][col_idx]["block_id"][0][0]
    add_module(block_id, page_id)
    session.save()


def add_column(block, row_idx, col_idx, page_id):
    uuid = generate_unique_id()
    block["layout"][row_idx].insert(col_idx+1, None)
    block["widths"][row_idx].insert(col_idx+1, 1.0)
    block["block_id"][row_idx].insert(col_idx+1, uuid)
    add_module(uuid, page_id)
    session.save()


def delete_block(block, row_idx, col_idx, page_id):

    ids = ids_in_block(block["layout"][row_idx][col_idx])
    ids.append(block["block_id"][row_idx][col_idx])

    # Check if we are deleting the last block
    layout = st.session_state["session"]["content"]["pages"][page_id]["custom_layout"]
    if (len(layout["layout"]) == 1 and len(layout["layout"][0]) == 1 
        and block is layout and row_idx == 0 and col_idx == 0):
        popup_error("You cannot delete the last block.")
        return

    for id in ids:
        remove_module(id, page_id)

    block["layout"][row_idx].pop(col_idx)
    block["widths"][row_idx].pop(col_idx)
    block["block_id"][row_idx].pop(col_idx)
    if len(block["layout"][row_idx]) == 0:  # ligne vide
        block["layout"].pop(row_idx)
        block["widths"].pop(row_idx)
        block["block_id"].pop(row_idx)

    session.save()


def get_block_by_id(block, block_id):
    if "block_id" in block:
        for i, row in enumerate(block["block_id"]):
            for j, bid in enumerate(row):
                if bid == block_id:
                    return block, i, j
                sub = block["layout"][i][j]
                if isinstance(sub, dict):
                    found = get_block_by_id(sub, block_id)
                    if found:
                        return found
    return None


def flatten(l):
    result = []
    for i in l:
        if isinstance(i, list):
            result += flatten(i)
        else:
            result.append(i)
    return result


def ids_in_block(block):
    
    ids = []

    if block is None:
        return ids

    if "block_id" in block:
        ids.append(block["block_id"])
        for i, row in enumerate(block["block_id"]):
            for j, bid in enumerate(row):
                sub = block["layout"][i][j]
                if isinstance(sub, dict):
                    found = ids_in_block(sub)

    ids = flatten(ids)

    return ids


def add_row_after(block, row_idx, page_id):
    uuid = generate_unique_id()
    if row_idx is None:
        block = {
            "layout": [[None]],
            "widths": [[1.0]],
            "block_id": [[uuid]],
            "block_type": "container"
        }
    else:
        block["layout"].insert(row_idx+1, [None])
        block["widths"].insert(row_idx+1, [1.0])
        block["block_id"].insert(row_idx+1, [uuid])

    add_module(uuid, page_id)
    session.save()


@st.dialog(":material/settings: Block Settings")
def chg_settings(block_id, page_id):
    settings = st.session_state["session"]["content"]["pages"][page_id]["modules"][block_id]["settings"]
    settings_new = settings.copy()

    st.divider()

    tile = st.columns([0.5, 0.5])

    ### Icon
    icon = tile[0].text_input("Icon", key=f"icon_{block_id}", value=settings.get("icon", ""), help="Icon of the Block (Material Symbols)")
    if icon: settings_new["icon"] = icon
    settings_new["icon_visible"] = tile[0].toggle("Show Icon", key=f"icon_visible_{block_id}", value=settings.get("title_visible", True), help="Show/Hide the Icon of the Block")


    ### Title
    title = tile[1].text_input("Title", key=f"title_{block_id}", value=settings.get("title", ""), help="Title of the Block")
    if title: settings_new["title"] = title
    settings_new["title_visible"] = tile[1].toggle("Show Title", key=f"title_visible_{block_id}", value=settings.get("title_visible", True), help="Show/Hide the Title of the Block")

    full_title = ""
    if settings_new["icon_visible"]: full_title += f"{settings_new['icon']} "
    if settings_new["title_visible"]: full_title += settings_new["title"]
    st.caption("Preview")
    st.info(full_title)

    ### Border
    st.caption("")
    settings_new["show_border"] = st.toggle("Show Border", key=f"show_border_{block_id}", value=settings.get("show_border", True), help="Show/Hide the Border of the Block")

    ### Widths
    st.divider()
    st.write("Block Widths")
    
    parents, ii, _ = get_block_by_id(st.session_state["session"]["content"]["pages"][page_id]["custom_layout"], block_id)
    widths = parents["widths"][ii]
    ids = parents["block_id"][ii]
    widths_new = widths.copy()

    tile = st.columns(len(widths))
    for i in range(len(widths)):
        tile[i].number_input(" ", key=f"width_select_{block_id}_{i}", value=widths_new[i], label_visibility="collapsed", step=0.1)
        widths_new[i] = float(st.session_state.get(f"width_select_{block_id}_{i}", widths[i]))

    st.caption("Preview")
    tile = st.columns(widths_new)
    for i in range(len(widths_new)):
        if block_id == ids[i]:
            tile[i].success("")
        else:
            tile[i].info("")
    

    ### Height
    st.caption("")
    height = st.slider("Block Height (in pixels)", key=f"height_{block_id}", min_value=0, max_value=1000, step=10, value=settings.get("height", 400), help="Height of the Block in pixels")
    if height:
        settings_new["height"] = height


    ### Save settings
    # st.divider()
    # st.write(settings_new)
    tile = st.columns([0.3, 0.4, 0.3])
    save = tile[1].button("Save", type="primary", args=(block_id, page_id), use_container_width=True)
    if save:
        st.session_state["session"]["content"]["pages"][page_id]["modules"][block_id]["settings"] = settings_new
        parents["widths"][ii] = widths_new.copy()
        session.save()
        st.rerun()



@st.dialog(":material/error: Error")
def popup_error(msg):
    st.error(msg)


def set_module(block_id, page_id, itab):
    module_name = st.session_state[f"selectmodule_{block_id}_{itab}"]
    st.session_state["session"]["content"]["pages"][page_id]["modules"][block_id]["settings"]["module"] = module_name
    st.session_state["session"]["content"]["pages"][page_id]["modules"][block_id]["settings"]["content"] = {}
    session.save()


def render_block(block, page_id, edition_mode, page_content):

    # options = [None] + list(m.MODULES.keys())

    if block["block_type"] in ["container", "tab"]:
        Nrows = len(block["layout"])
        for i in range(Nrows):
            cols = st.columns(block["widths"][i])
            for j in range(len(cols)):
                sub_block = block["layout"][i][j]
                block_id = block["block_id"][i][j]

                settings = page_content["modules"][block_id]["settings"]
                module = settings["module"]

                if edition_mode:
                    show_border=True
                else:
                    show_border = settings["show_border"]

                with cols[j].container(border=show_border):

                    # idx = options.index(module)
                    title = ""
            
                    if settings["icon_visible"]: title += f"{settings['icon']} "
                    if settings["title_visible"]: title += settings["title"]

                    if edition_mode:
                        # 1st Block Row
                        tile = st.columns([0.1, 0.8, 0.1])
                        tile[0].button(":material/settings:", key=f"settings_{block_id}", use_container_width=True,
                                    on_click=chg_settings, args=(block_id, page_id), help="Edit Block Settings")
                        tile[1].caption(title)
                        tile[2].button(":material/arrow_forward:", key=f"addcol_{block_id}", use_container_width=True,
                                    on_click=lambda b=block,i=i,j=j:add_column(b,i,j,page_id), help="Add Block to the Right")
                        
                        # 2nd Block Row
                        tile = st.columns([0.9, 0.1])
                        # tile[0].selectbox(f"{block_id}", options=options, index=idx, on_change=lambda bid=block_id:set_module(bid,page_id),
                        #                 key=f"selectmodule_{block_id}", label_visibility="collapsed", disabled=False)
                        module_name = st.session_state["session"]["content"]["pages"][page_id]["modules"][block_id]["settings"]["module"]
                        if module_name is None : module_name = "Select Module"
                        with tile[0].popover(f"{module_name}", use_container_width=True):

                            menus = list(m.MODULES.keys())
                            tabs = st.tabs(menus)
                            for itab, (tab, name) in enumerate(zip(tabs, menus)):
                                with tab:
                                    module_list = [None]+list(m.MODULES[name].keys())
                                    st.pills(" ", module_list, key=f"selectmodule_{block_id}_{itab}",
                                                    on_change=lambda bid=block_id, pid=page_id, it=itab: set_module(bid, pid, it),
                                                    label_visibility="collapsed")
                            
                        tile[1].button(":material/delete:", key=f"del_{block_id}", type="primary", use_container_width=True,
                                    on_click=lambda b=block,i=i,j=j:delete_block(b,i,j,page_id), help="Delete Block")
                        
                        # 3rd Block Row
                        if sub_block is None:
                            st.button(":material/arrow_downward:", key=f"addsub_{block_id}", use_container_width=True,
                                    on_click=lambda b=block,i=i,j=j:add_sub_block(b,i,j, page_id), help="Add Row") 
                        elif sub_block["layout"] == []:     
                            st.button(":material/arrow_downward:", key=f"addsub_{block_id}", use_container_width=True,
                                    on_click=lambda b=block,i=i,j=j:add_sub_block(b,i,j, page_id), help="Add Row") 
                    else:
                        if title not in ["", None] and not title.isspace():
                            st.subheader(title)
                        show_module(block_id, page_id)

                    if isinstance(sub_block, dict):
                        render_block(sub_block, page_id, edition_mode, page_content)

            if edition_mode:
                st.button(":material/arrow_downward:", key=f"addrow_{block['block_id'][i][0]}", use_container_width=True,
                    on_click=lambda b=block,i=i:add_row_after(b, i, page_id), help="Add Row")


def load(page_id):

    page_content = st.session_state["session"]["content"]["pages"][page_id]

    tile = st.columns([0.9, 0.1])
    edition_mode = tile[1].toggle(f"Edition Mode", key=f"edition_{page_id}", value=False)

    if page_content["custom_layout"] == {}:
        page_content["custom_layout"] = default_block()
        add_module(page_content["custom_layout"]["block_id"][0][0], page_id)

    render_block(page_content["custom_layout"], page_id, edition_mode, page_content)


def add_module(block_id, page_id):
    modules = st.session_state["session"]["content"]["pages"][page_id]["modules"]
    modules[block_id] = {
        "settings" : {
            "title": "",
            "icon": "",
            "title_visible": True,
            "icon_visible": True,
            "show_border": True,
            "height": 400,
            "module": None,
        },
        "content" : {}
    }


def remove_module(block_id, page_id):
    modules = st.session_state["session"]["content"]["pages"][page_id]["modules"]
    del modules[block_id]
    session.save()

def show_module(block_id, page_id):
    module_dict = st.session_state["session"]["content"]["pages"][page_id]["modules"][block_id]
    module_name = module_dict["settings"]["module"]
    if module_name is not None:
        func = m.MODULES_LIST[module_name]
        func(module_dict)
    
    #############################################################
    # Page Content
    import pickle as pkl
    import pandas as pd

    inventory_file = "/media/flavien/WORK/these/tools/inventory_alsace.pkl"
                    
    with open(inventory_file, "rb") as f:
        inventory = pkl.load(f)

    inventory = pd.DataFrame(inventory)
    inventory = inventory.drop(columns=["geometry"])
    inventory['Channels'] = inventory['Channels'].apply(lambda x: list(dict.fromkeys(x)))

    # ########### Configure Layout ###########

    # tile = st.container()
    # m.dataframe_stations(tile, inventory, height=module_dict["settings"]["height"])
