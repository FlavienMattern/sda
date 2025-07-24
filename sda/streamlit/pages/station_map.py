from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
import streamlit as st

st.title(":material/map: Map Explorer")
st.divider()
database.status()

if database.is_loaded():
    ########### Prepare Data ###########

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
    modules.map_stations(tile, inventory)

    tile = row[1].container()
    modules.dataframe_stations(tile, inventory)