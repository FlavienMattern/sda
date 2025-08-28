import streamlit as st
import os
import pandas as pd
import shutil


def layout(title):
    return f"""
############# Page Header #############
from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import custom_pages as page
import streamlit as st
st.title(":material/add_chart: {title}")
st.divider()
database.status()
#######################################
    """



@st.dialog(":material/warning: Error")
def popup_error(msg):
    st.error(msg)


@st.dialog(":material/warning: Caution")
def popup_warning(msg):
    st.warning(msg)


def get_pages():

    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    pages_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages")
    pages_filename = os.path.join(pages_folder, "pages.txt")

    if not os.path.exists(pages_filename):
        pages = pd.DataFrame({
                    'page_name': [],
                    'page_folder': []
                })
        pages.index.name = 'id'
    else:
        pages = pd.read_csv(pages_filename, delimiter=",")
        pages.set_index("id", inplace=True)

    return pages


def create(name):

    if st.session_state.get("session")["content"] is None:
        st.session_state["session"]["content"] = {}

    if "custom_pages" not in st.session_state.get("session")["content"].keys():
        st.session_state["session"]["content"]["custom_pages"] = {}

    if name in ["", None] or name.isspace():
        popup_error(f"You need to enter a valid name !")
        return

    if name in st.session_state.get("session")["content"]["custom_pages"].keys():
        popup_error(f"A custom page with the name **{name}** already exists !")
        return

    pages = get_pages()
    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    
    if len(pages) == 0:
        page_id = 0
    else:
        page_id = max(list(pages.index)) + 1

    # Update list of pages
    pages_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages")
    pages_filename = os.path.join(pages_folder, "pages.txt")
    pages.loc[page_id] = [name, f"page_{page_id:03d}"]
    
    os.makedirs(pages_folder, exist_ok=True)

    pages.to_csv(pages_filename)

    # Create page layout
    custom_page_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages", f"page_{page_id:03d}")
    custom_page_filename = os.path.join(custom_page_folder, f"layout_{page_id:03d}.py")

    if os.path.exists(custom_page_folder):
        shutil.rmtree(custom_page_folder)
    
    os.makedirs(custom_page_folder, exist_ok=True)
    
    with open(custom_page_filename, "w") as f:
        f.write(layout(name))

    st.rerun()



def clean(id):

    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    custom_page_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages", f"page_{id:03d}")
    custom_page_filename = os.path.join(custom_page_folder, f"layout_{id:03d}.py")
    pages = get_pages()
    page_name = pages[pages.index == id].page_name.values[0]
    
    with open(custom_page_filename, "w") as f:
        f.write(layout(page_name))

    st.rerun()


@st.dialog(":material/warning: Caution !")
def clean_check(id):
    pages = get_pages()
    page_name = pages[pages.index == id].page_name.values[0]
    st.warning(f":material/warning: You are about to clean the custom page : **{page_name}**. You will loose all information on this page. Close this popup if it was a mistake.")
    if st.button(":material/check: Clean Page"):
        clean(id)


def remove(id):

    # Delete Folder Page
    wdir = st.session_state.get("database")["settings"]["wdir"]
    session_id =  st.session_state.get("session")["settings"]["id"]
    custom_page_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages", f"page_{id:03d}")

    if os.path.exists(custom_page_folder):
        shutil.rmtree(custom_page_folder)

    # Delete Page in Database
    pages = get_pages()
    pages = pages.drop(id)
    pages_folder = os.path.join(wdir, "streamlit", f"session_{session_id:03d}", "custom_pages")
    pages_filename = os.path.join(pages_folder, "pages.txt")
    pages.to_csv(pages_filename)

    st.rerun()


@st.dialog(":material/warning: Caution !")
def remove_check(id):
    pages = get_pages()
    page_name = pages[pages.index == id].page_name.values[0]
    st.warning(f":material/warning: You are about to permanently remove the custom page : **{page_name}**. You will loose all information on this page. Close this popup if it was a mistake.")
    if st.button(":material/check: Remove Page"):
        remove(id)

def visibility(id):
    pages = get_pages()
    page_name = pages[pages.index == id].page_name.values[0]