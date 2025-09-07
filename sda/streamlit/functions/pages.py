import streamlit as st
import uuid, os
from sda.streamlit.functions import session
from sda.streamlit.functions import custom_pages as cpages


def generate_unique_id():
    return str(uuid.uuid4())


def get_pages():
    return list(st.session_state["session"]["content"]["pages"].keys())


def get_page_names():
    
    page_names = []
    for page_id in st.session_state["session"]["content"]["pages"].keys():
        page_names.append(st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["title"])
        
    return page_names


def get_page_content(page_id):
    return st.session_state["session"]["content"]["pages"][page_id]


def get_page_id(file):
    
    if st.session_state.get("session")["content"] is None:
        return None
    
    if "pages" not in st.session_state.get("session")["content"].keys():
        return None
    
    for page_id in st.session_state["session"]["content"]["pages"].keys():
        if st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["file"] == file:
            return page_id
    return None


def is_visible(page_id):
    if page_id is None:
        return True
    else:
        return st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["visible"]



def load_page(file):
    
    page_id = get_page_id(file)
    page_content = st.session_state["session"]["content"]["pages"][page_id]
    page_name = page_content["page_settings"]["title"]
    page_icon = page_content["page_settings"]["icon"]
    custom_page = not page_content["page_settings"]["default_page"]
    
    if file != "pages/dashboard.py":
        st.title(page_icon + " " + page_name)
        st.divider()
    
    if custom_page:
        
        cpages.load(page_id)
        
        if session.is_dev_mode():
            st.divider()
            st.write(page_content)
        
    
def remove(page_id):

    # Delete Folder Page
    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    custom_page_filename = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages", f"{page_id}.py")

    if os.path.exists(custom_page_filename):
        os.remove(custom_page_filename)

    # Delete Page in Database
    st.session_state["session"]["content"]["pages"].pop(f"{page_id}", None)

    session.save()
    st.rerun()
    
    
def layout(page_file):
    return f"""
############# Page Header #############
page_file = "{page_file}"
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import pages
database.status()
if database.is_loaded():
    page_id = pages.get_page_id(page_file)
    pages.load_page(page_file)
#######################################
    """
    
    
def change_order(page_id, order):
    
    page_list = get_pages()
    
    if order == "UP":
        page1 = page_id
        page_cur_pos = page_list.index(page_id)
        page_new_pos = page_cur_pos - 1
        page2 = get_pages()[page_new_pos]
        
    else:
        page1 = page_id
        page_cur_pos = page_list.index(page_id)
        page_new_pos = page_cur_pos + 1
        page2 = get_pages()[page_new_pos]
    
    pages = st.session_state["session"]["content"]["pages"]
    pages[page1], pages[page2] = pages[page2], pages[page1]
    
    session.save()
    
    
def clean(page_id):
    st.session_state["session"]["content"]["pages"][page_id]["modules"] = {}
    st.session_state["session"]["content"]["pages"][page_id]["custom_layout"] = {}
    session.save()
    st.rerun()
    
    
@st.dialog(":material/warning: Caution !")
def clean_check(page_id):
    page_name = get_page_content(page_id)["page_settings"]["title"]
    page_icon = get_page_content(page_id)["page_settings"]["icon"]
    st.warning(f":material/warning: You are about to clean the custom page : **{page_icon} {page_name}**. You will loose all information on this page. Close this popup if it was a mistake.")
    if st.button(":material/check: Clean Page"):
        clean(page_id)


@st.dialog(":material/warning: Caution !")
def remove_check(page_id):
    page_name = get_page_content(page_id)["page_settings"]["title"]
    page_icon = get_page_content(page_id)["page_settings"]["icon"]
    st.warning(f":material/warning: You are about to permanently remove the custom page : **{page_icon} {page_name}**. You will loose all information on this page. Close this popup if it was a mistake.")
    if st.button(":material/check: Remove Page"):
        remove(page_id)
        

@st.dialog(":material/edit: Page Settings")
def edit_settings(page_id):
    page_content = get_page_content(page_id)
    with st.form(f"edit_page_{page_id}_form"):
        title = st.text_input("Page Name", value=page_content["page_settings"]["title"])
        icon = st.text_input("Page Icon", value=page_content["page_settings"]["icon"])
        st.caption("For the list of available icons, please refer to the [Material Design Icons](https://fonts.google.com/icons?selected=Material+Icons).")
        
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            if title in ["", None] or title.isspace():
                st.error(f"You need to enter a valid name !")
                return

            if title != page_content["page_settings"]["title"] and title in get_page_names():
                st.error(f"A page with the name **{title}** already exists !")
                return
            
            st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["title"] = title
            st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["icon"] = icon
            
            session.save()
            st.rerun()


def visibility(id):
    get_page_id = f"{id}"
    current_visibility = st.session_state["session"]["content"]["pages"][get_page_id]["page_settings"]["visible"]
    if current_visibility:
        st.session_state["session"]["content"]["pages"][get_page_id]["page_settings"]["visible"] = False
    else:
        st.session_state["session"]["content"]["pages"][get_page_id]["page_settings"]["visible"] = True
        
    session.save()
    
    
    
def create(name):

    if name in ["", None] or name.isspace():
        popup_error(f"You need to enter a valid name !")
        return

    if name in get_page_names():
        popup_error(f"A page with the name **{name}** already exists !")
        return

    page_list = get_pages()
    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    
    page_id = generate_unique_id()

    # Update list of pages
    pages_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages")
    
    os.makedirs(pages_folder, exist_ok=True)
    
    # Create page layout
    custom_page_filename = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages", f"{page_id}.py")

    if os.path.exists(custom_page_filename):
        os.remove(custom_page_filename)
    
    Page(file=custom_page_filename, title=name, icon=":material/instant_mix:", removable=True, default_page=False, init_tabs=True, page_id=page_id)
    
    with open(custom_page_filename, "w") as f:
        f.write(layout(custom_page_filename))

    session.save()
    st.rerun()
    
@st.dialog(":material/warning: Error")
def popup_error(msg):
    st.error(msg)


@st.dialog(":material/warning: Caution")
def popup_warning(msg):
    st.warning(msg)


class Page:

    def __init__(self, file, title, icon, removable=True, default_page=False, init_tabs=True, page_id=None):

        self.show_block = False
        self.visible = True
        self.removable = removable
        self.title = title
        self.default_page = default_page
        self.init_tabs = init_tabs
        self.file = file
        self.title = title
        self.icon = icon

        if st.session_state.get("session")["content"] is None:
            st.session_state["session"]["content"] = {}

        if "pages" not in st.session_state.get("session")["content"].keys():
            st.session_state["session"]["content"]["pages"] = {}

        # Check if page is already stored
        if page_id is not None:
            self.page_id = page_id
            id_exists = False
        else:
            id_exists = False
            for page_id in st.session_state["session"]["content"]["pages"].keys():
                if title == st.session_state["session"]["content"]["pages"][page_id]["page_settings"]["title"]:
                    self.page_id = page_id
                    id_exists = True
                    break
            if not id_exists:
                self.page_id = None

        if not id_exists:
            self.page_id = self.create_page(file, title, icon, removable=removable, default_page=default_page, page_id=self.page_id)
        else:
            st.session_state["session"]["content"]["pages"][self.page_id]["page_settings"] = {
                "title": title,
                "icon": icon,
                "file": self.file,
                "visible": self.visible,
                "removable": removable,
                "default_page": default_page,
            }
            
        if not default_page:
            if "custom_layout" not in st.session_state["session"]["content"]["pages"][self.page_id].keys():
                st.session_state["session"]["content"]["pages"][self.page_id]["custom_layout"] = {}


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
        
        
    def create_page(self, file, title, icon, removable=True, default_page=False, page_id=None):
        
        if page_id is None:
            page_id = generate_unique_id()
        
        # Define page id (if not found previously)       
        default_settings = {
            "show_title": True,
            "show_border": True,
            "height": 400,
        }

        st.session_state["session"]["content"]["pages"][page_id] = {
            "page_settings": {
                "title": title,
                "file": file,
                "icon": icon,
                "visible": self.visible,
                "removable": removable,
                "default_page": default_page,
            },
            "modules": {}
        }

        return page_id