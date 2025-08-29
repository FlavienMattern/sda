page_title = ":material/experiment: [DEV] Sandbox"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import session
from sda.streamlit.functions import tmp
from sda.streamlit.functions import pages
import streamlit as st

database.status()

if database.is_loaded():
    p = pages.Page(page_title, visible=True, removable=True, default_page=True, init_tabs=True)


    
