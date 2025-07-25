from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
import streamlit as st

st.title(":material/vital_signs: Waveform Viewer")
st.divider()
database.status()

if database.is_loaded():
    ########### Prepare Data ###########

    import pickle as pkl
    import pandas as pd
    from obspy import read, UTCDateTime
    from datetime import datetime, timedelta
    import plotly.graph_objects as go
    import plotly.express as px
    import numpy as np
    # import altair as alt
    # alt.theme.enable('quartz')
    
    net = "FR"
    sta = "HOHE"
    loc = "00"
    cha = "HHZ"
    starttime = "2020-01-01 00:00:00"
    endtime   = "2020-01-01 01:00:00"
    
    starttime = datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S")
    endtime = datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S")

    df = database.get_db_content("DATASET")
    df["STARTTIME"] = pd.to_datetime(df["STARTTIME"], format="%Y-%m-%d %H:%M:%S.%f")
    df["ENDTIME"] = pd.to_datetime(df["STARTTIME"], format="%Y-%m-%d %H:%M:%S.%f")
    
    df = df[
        (df["STATION"] == sta) &
        (df["NETWORK"] == net) &
        (df["LOCATION"] == loc) &
        (df["CHANNEL"] == cha) &
        (df["ENDTIME"] >= starttime) &
        (df["STARTTIME"] <= endtime)
    ]


    ########### Configure Layout ###########
    stream = read().clear()
    for f in list(df["FILE"]):
        stream += read(f)
    stream.merge(method=1, interpolation_samples=0, fill_value=None)
    stream.trim(UTCDateTime(starttime), UTCDateTime(endtime))

    
    t = pd.date_range(start=stream[0].stats.starttime.datetime,
                      end=stream[0].stats.endtime.datetime,
                      periods=len(stream[0]))
        
    dt = stream[0].stats.delta
    
    data = pd.DataFrame({
        "Time" : t[::10],
        "y1" : stream[0].data[::10],
        "y2" : -stream[0].data[::10]
    })
    data.set_index("Time", inplace=True)
    
    with st.container(border=True):
        st.button(":material/dehaze:")
        st.button(":material/arrow_menu_open:")
        st.button(":material/arrow_menu_close:")
        
        placeholder = st.empty()
        placeholder.write("Loading Waveform...")
        
        fig = px.line(data, y=["y1", "y2"])
        fig.update_xaxes(
            rangeslider_visible=True,
            rangeslider=dict(
                bgcolor="#F5F5F5",
                bordercolor="#B5B5B5",
                borderwidth=1,
                thickness=0.1
                )
            )

        st.plotly_chart(fig, config = {'scrollZoom': True})

        placeholder.empty()