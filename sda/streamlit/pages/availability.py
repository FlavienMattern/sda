page_file = "pages/availability.py"

from sda.streamlit.functions import db_utils as database
from sda.streamlit.functions import modules
from sda.streamlit.functions import pages
import streamlit as st

database.status()

def dates_to_ranges(jours):
    # Convertir en datetime pandas et trier
    dates = pd.to_datetime(jours)
    dates = np.sort(dates.unique())  # supprime doublons et trie

    if len(dates) == 0:
        return [], []

    # Cas où il n'y a qu'un seul jour
    if len(dates) == 1:
        start_str = [pd.Timestamp(dates[0]).strftime("%Y-%m-%d")]
        end_str = [(pd.Timestamp(dates[0]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")]
        return start_str, end_str

    # Calculer les différences entre jours consécutifs
    diff = np.diff(dates).astype('timedelta64[D]')

    # Indices où il y a un "trou" (>1 jour)
    idx = np.where(diff != 1)[0]

    # Début et fin des plages
    if len(idx) == 0:
        starts = np.array([dates[0]])
        ends = np.array([dates[-1] + np.timedelta64(1, 'D')])
    else:
        starts = np.insert(dates[idx + 1], 0, dates[0])
        ends = np.append(dates[idx] + np.timedelta64(1, 'D'), dates[-1] + np.timedelta64(1, 'D'))

    # Convertir en chaînes en utilisant pd.Timestamp
    start_str = [d for d in starts]
    end_str = [d for d in ends]

    return starts, ends

if database.is_loaded():

    import streamlit as st
    import plotly.express as px
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    from stqdm import stqdm
    import os
    import pickle as pkl


    # Load page
    page_id = pages.get_page_id(page_file)
    pages.load_page(page_file)

    wdir = st.session_state.get("database")["settings"]["wdir"]
    placeholder = st.empty()
    

    ###############################
    availability_file = os.path.join(wdir, "availability", "daily_availability.pkl")
    if not os.path.exists(availability_file):
        placeholder.info("Fetching data availability... (**First Run** : It may take some time to scan all files.)")
        db_content = st.session_state.get("database")["content"]
        keys = list(db_content.keys())
        df = db_content["DATASET"]

        data_sta = {}

        for idx, row in stqdm(df.iterrows(), total=len(df), desc="Collecting Time Intervals "):
            sta_code = row["NETWORK"] + "." + row["STATION"]
            npts = row["NPTS"]
            dt = row["DELTA"]
            starttime = row["STARTTIME"]
            if isinstance(starttime, str):
                starttime = datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S.%f")

            endtime = starttime + timedelta(seconds=int(npts)*float(dt))

            if sta_code not in data_sta.keys():
                data_sta[sta_code] = []

            tlist = pd.date_range(start=starttime, end=endtime, freq="1D")
            for t in tlist:
                data_sta[sta_code].append(datetime.strftime(t, "%Y-%m-%d"))

        data = []
        for key in data_sta.keys():
            data_sta[key] = list(set(data_sta[key]))
            data_sta[key].sort()
            period_start, period_end = dates_to_ranges(data_sta[key])
            for idx, start in enumerate(period_start):
                end = period_end[idx]
                data.append({"station": key, "start": start, "end": end})

        # Créer DataFrame
        df = pd.DataFrame(data)
        df['start'] = pd.to_datetime(df['start'])
        df['end'] = pd.to_datetime(df['end'])
        df['end_str'] = df['end'].dt.strftime("%Y-%m-%d")
        df['start_str'] = df['start'].dt.strftime("%Y-%m-%d")

        os.makedirs(os.path.join(wdir, "availability"), exist_ok=True)

        with open(availability_file, "wb") as f:
            pkl.dump(df, f)
    else:
        placeholder.info("Fetching data availability...")
        with open(availability_file, "rb") as f:
            df = pkl.load(f)

    df = df.sort_values("station")

    stations = list(set(list(df["station"])))

    fig = px.timeline(df, x_start="start", x_end="end", y="station", color="station",
                      height=20*len(stations), facet_col_spacing=0.9, facet_row_spacing=0.9,
                      color_discrete_sequence=["#D0D7E7", "#B2BED7", "#93A5C8", "#758BB8", "#5772A8", "#475D8A", "#3C4F75", "#28344D"],
                      custom_data=["start_str","end_str"])
    fig.update_yaxes(title_text=None)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgrey")
    fig.update_layout(showlegend=False, yaxis=dict(fixedrange=True), xaxis=dict(fixedrange=False))
    fig.update_traces(hovertemplate="%{customdata[0]} - %{customdata[1]}")

    st.plotly_chart(fig, use_container_width=True)
    placeholder.empty()