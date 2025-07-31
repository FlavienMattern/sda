page_title = ":material/experiment: [DEV] Sandbox"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import session
from sda.streamlit.functions import tmp
from sda.streamlit.functions import page
import streamlit as st

database.status()

if database.is_loaded():

    # Page Content
    import pickle as pkl
    import pandas as pd

    inventory_file = "/media/flavien/WORK/these/tools/inventory_alsace.pkl"
                    
    with open(inventory_file, "rb") as f:
        inventory = pkl.load(f)

    inventory = pd.DataFrame(inventory)
    inventory = inventory.drop(columns=["geometry"])
    inventory['Channels'] = inventory['Channels'].apply(lambda x: list(dict.fromkeys(x)))

    tmp.set("stations_inventory", inventory)
    
    # Load page
    p = page.Page(page_title)
    # p = page.Page(page_title, visible=True, removable=False, default_page=True)


    
