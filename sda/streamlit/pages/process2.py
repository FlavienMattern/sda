page_file = "pages/process2.py"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import pages
import streamlit as st

database.status()

if database.is_loaded():
    
    # Load page
    page_id = pages.get_page_id(page_file)
    pages.load_page(page_file)

    # Page Content