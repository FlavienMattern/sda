import streamlit as st
import pydeck
from sda.streamlit.functions import map_utils



def dataframe_stations(tile, inventory):
    """Container with a dataframe of all seismic stations and metadata

    Args:
        tile (_type_): The streamlit containter
        inventory (_type_): A DataFrame object containing stations metadata
    """
    tile.title(":material/data_table: Station Metadata")
    tile.dataframe(inventory, height=800)



def map_stations(tile, inventory, lat_col="Latitude", lon_col="Longitude"):
    """Container with a map of seismic stations.

    Args:
        tile (_type_): The streamlit containter
        inventory (_type_): A DataFrame object containing stations metadata
        lat_col (str, optional): DataFrame column with latitudes. Defaults to "Latitude".
        lon_col (str, optional): DataFrame column with longitudes. Defaults to "Longitude".
    """
    
    tile.title(":material/map_search: Station Map")

    stations_layer = pydeck.Layer(
        "ScatterplotLayer",
        data=inventory,
        id="station_inventory",
        get_position=[lon_col, lat_col],
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
        latitude=lat0, longitude=lon0, controller=True, zoom=zoom, pitch=0, bearing=0,
    )

    chart = pydeck.Deck(
        [stations_layer],
        map_provider = "carto",
        map_style = "road",
        initial_view_state=view_state,
        tooltip={"text": "{Network}.{Station}\n({Longitude},{Latitude},{Elevation})\n{Channels}"},
    )

    event = tile.pydeck_chart(chart, on_select="rerun", selection_mode="single-object")
    event.selection