page_file = "pages/sandbox.py"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import session
from sda.streamlit.functions import tmp
from sda.streamlit.functions import pages
import streamlit as st

database.status()

if database.is_loaded():
    
    page_id = pages.get_page_id(page_file)
    pages.load_page(page_file)
    
    
    if session.is_dev_mode():
        st.divider()
        st.write(st.session_state["session"]["content"]["pages"][page_id])


    
