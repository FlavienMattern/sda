import streamlit as st
import pydeck
from sda.streamlit.functions import map_utils


def dataframe_stations(module):
    """Container with a dataframe of all seismic stations and metadata

    Args:
        tile (_type_): The streamlit containter
        inventory (_type_): A DataFrame object containing stations metadata
    """
    import pickle as pkl
    import pandas as pd

    inventory_file = "/media/flavien/WORK/these/tools/inventory_alsace.pkl"
                    
    with open(inventory_file, "rb") as f:
        inventory = pkl.load(f)

    inventory = pd.DataFrame(inventory)
    inventory = inventory.drop(columns=["geometry"])
    inventory['Channels'] = inventory['Channels'].apply(lambda x: list(dict.fromkeys(x)))

    st.subheader(":material/data_table: Station Metadata")
    st.dataframe(inventory, height=module["settings"]["height"])



def map_stations(module):
    """Container with a map of seismic stations.

    Args:
        tile (_type_): The streamlit containter
        inventory (_type_): A DataFrame object containing stations metadata
        lat_col (str, optional): DataFrame column with latitudes. Defaults to "Latitude".
        lon_col (str, optional): DataFrame column with longitudes. Defaults to "Longitude".
    """
    
    MAPBOX_TOKEN = "pk.eyJ1IjoiZm1hdHRlcm4iLCJhIjoiY21lc2duY29xMDJvOTJpc2IzemtweXU0aCJ9.sj6nuBio6x5gxQN0N9_Mng"
    
    import pickle as pkl
    import pandas as pd

    inventory_file = "/media/flavien/WORK/these/tools/inventory_alsace.pkl"
                    
    with open(inventory_file, "rb") as f:
        inventory = pkl.load(f)

    inventory = pd.DataFrame(inventory)
    inventory = inventory.drop(columns=["geometry"])
    inventory['Channels'] = inventory['Channels'].apply(lambda x: list(dict.fromkeys(x)))

    lat_col="Latitude"
    lon_col="Longitude"

    st.subheader(":material/map_search: Station Map")

    ICON_URL = "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png"
    icon_mapping = {
        "marker": {
            "x": 0, "y": 0, "width": 128, "height": 128,
            "anchorY": 128
        }
    }
    inv = inventory.copy()
    inv["icon"] = "marker"

    stations_layer = pydeck.Layer(
        "IconLayer",
        data=inv,
        id="station_inventory",
        get_position=[lon_col, lat_col],
        get_icon="icon",
        icon_atlas=ICON_URL,
        icon_mapping=icon_mapping,
        get_size = 20,
        pickable=True,
        auto_highlight=True,
    )

    latmin = min(inv[lat_col])
    latmax = max(inv[lat_col])
    lonmin = min(inv[lon_col])
    lonmax = max(inv[lon_col])
    lon0, lat0, zoom = map_utils.get_bounds(lonmin, lonmax, latmin, latmax)

    view_state = pydeck.ViewState(
        latitude=lat0, longitude=lon0, controller=True, zoom=zoom, pitch=0, bearing=0,
    )

    chart = pydeck.Deck(
        layers = [stations_layer],
        map_provider = None,
        initial_view_state=view_state,
        tooltip={"text": "{Network}.{Station}\n({Longitude},{Latitude},{Elevation})\n{Channels}"},
        map_style="mapbox://styles/mapbox/outdoors-v12",
        api_keys={"mapbox": MAPBOX_TOKEN},
    )

    event = st.pydeck_chart(chart, on_select="rerun", selection_mode="multi-object", height=module["settings"]["height"])
    event.selection


MODULES = {
    "Stations Metadata": dataframe_stations,
    "Stations Map":      map_stations,
}