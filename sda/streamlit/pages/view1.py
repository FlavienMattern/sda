page_title = ":material/map: View 1"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import pages
import streamlit as st

database.status()

if database.is_loaded():
    
    # Load page
    p = pages.Page(page_title, visible=True, removable=False, default_page=True)

    # Page Content