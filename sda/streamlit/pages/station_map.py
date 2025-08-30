page_file = "pages/station_map.py"

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
    import pickle as pkl
    import pandas as pd

    inventory_file = "/media/flavien/WORK/these/tools/inventory_alsace.pkl"
                    
    with open(inventory_file, "rb") as f:
        inventory = pkl.load(f)

    inventory = pd.DataFrame(inventory)
    inventory = inventory.drop(columns=["geometry"])
    inventory['Channels'] = inventory['Channels'].apply(lambda x: list(dict.fromkeys(x)))

    ########### Configure Layout ###########

    row = st.columns([0.5, 0.5])

    tile = row[0].container()
    modules.map_stations(tile, inventory, height=600)

    tile = row[1].container()
    modules.dataframe_stations(tile, inventory, height=600)