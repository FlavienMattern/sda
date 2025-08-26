import streamlit as st
import pydeck
from sda.streamlit.functions import map_utils


def run(id):
    pass

def list():
    return {
        "dataframe_stations": "Stations Metadata",
        "map_stations": "Station Map",
    }

def dataframe_stations(inventory):
    """Container with a dataframe of all seismic stations and metadata

    Args:
        tile (_type_): The streamlit containter
        inventory (_type_): A DataFrame object containing stations metadata
    """
    st.subheader(":material/data_table: Station Metadata")
    st.dataframe(inventory, height=800)



def map_stations(inventory, lat_col="Latitude", lon_col="Longitude", ele_col="Elevation"):
    """Container with a map of seismic stations.

    Args:
        tile (_type_): The streamlit containter
        inventory (_type_): A DataFrame object containing stations metadata
        lat_col (str, optional): DataFrame column with latitudes. Defaults to "Latitude".
        lon_col (str, optional): DataFrame column with longitudes. Defaults to "Longitude".
    """
    
    MAPBOX_TOKEN = "to be changed"
    
    inventory[ele_col] = inventory[ele_col]/1e3
    
    st.subheader(":material/map_search: Station Map")

    stations_layer = pydeck.Layer(
        "ScatterplotLayer",
        data=inventory,
        id="station_inventory",
        get_position=[lon_col, lat_col],
        get_elevation=ele_col,
        elevation_scale=10,
        get_color="[255, 75, 75]",
        pickable=True,
        auto_highlight=True,
        get_radius=500,  
    )

    latmin = min(inventory[lat_col])
    latmax = max(inventory[lat_col])
    lonmin = min(inventory[lon_col])
    lonmax = max(inventory[lon_col])
    lon0, lat0, zoom = map_utils.get_bounds(lonmin, lonmax, latmin, latmax)

    view_state = pydeck.ViewState(
        latitude=lat0, longitude=lon0, controller=True, zoom=zoom, pitch=50, bearing=0,
    )
    
    # Terrain Layer
    terrain_layer = pydeck.Layer(
        "TerrainLayer",
        data = None,
        elevation_decoder={
            "rScaler": 256,
            "gScaler": 1,
            "bScaler": 1/256,
            "offset": -32768
        },
        texture=f"https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/256/{{z}}/{{x}}/{{y}}?access_token={MAPBOX_TOKEN}",
        elevation_data="https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
        wireframe = False,
        elevation_scale = 100
    )
    
    chart = pydeck.Deck(
        layers=[stations_layer, terrain_layer],
        initial_view_state=view_state,
        map_style=None,   # on ne met pas de style par-dessus
        api_keys={"mapbox": MAPBOX_TOKEN},
    )

    # chart = pydeck.Deck(
    #     layers = [stations_layer],
    #     map_provider = None,
    #     initial_view_state=view_state,
    #     tooltip={"text": "{Network}.{Station}\n({Longitude},{Latitude},{Elevation})\n{Channels}"},
    #     api_keys={"mapbox": MAPBOX_TOKEN},
    # )

    event = st.pydeck_chart(chart, on_select="rerun", selection_mode="multi-object", height=1000)
    event.selection