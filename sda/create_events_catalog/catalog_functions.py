import numpy as np
import sqlite3
import pandas as pd
import re

# Fonctions OBSPY
from obspy import read
from obspy.signal.trigger import recursive_sta_lta
from obspy.signal.trigger import trigger_onset


priority = ["HH","HN","BH","BN","EH","SH","EL","LH"]



def channelSort(string_list):
    return sorted(string_list, key=lambda x: priority.index(x[:2]))



def sta_lta(Trace, config):
    dt = Trace.stats.delta
    fs = 1./dt
    t = np.linspace(0, len(Trace)*dt, len(Trace))
    
    rsta  = recursive_sta_lta(Trace.data, nsta=int(config["lenSTA"]*fs), nlta=int(config["lenLTA"]*fs))
    trigs = trigger_onset(rsta, config["triggerHigh"], config["triggerLow"])
    trigONidx  = trigs[0][0]
    trigOFFidx = trigs[0][1]
    trigON     = t[trigONidx]
    trigOFF    = t[trigOFFidx]
    
    return trigON, trigOFF



def ProcessBeforeCodaSelect(Trace, t0, inventory, config):
    # Preparing Trace
    Trace.trim(starttime=t0+config["starttimeEvent"],
                endtime=t0+config["endtimeEvent"])
    
    # Processing Trace
    if config["remove_response"]:
        Trace.attach_response(inventory)
        Trace.remove_response(water_level=config["water_level"],
                              pre_filt=config["response_prefilt"],
                              hide_sensitivity_mismatch_warning=True)
    Trace.filter("bandpass", freqmin=config["freqMin"], freqmax=config["freqMax"],
                 corners=3, zerophase=True)
    
    return Trace



def PreProcessTrace(Trace, t0, inventory, config):
    
    # Resample Trace
    Trace.resample(config["NewFrequence"])

    # Remove response
    if config["remove_response"]:
        Trace.attach_response(inventory)
        Trace.remove_response(water_level=config["water_level"],
                              pre_filt=config["response_prefilt"],
                              hide_sensitivity_mismatch_warning=True)
    
    # Bandpass filtering
    Trace.filter("bandpass", freqmin=config["freqMin"], freqmax=config["freqMax"],
                 corners=3, zerophase=True)
    
    return Trace



def functionRegex(value, pattern):
    c_pattern = re.compile(r"\b" + pattern.lower() + r"\b")
    return c_pattern.search(value) is not None
    
    

def LoadTraces(db_file, config, start="1970-01-01", end="2100-01-01"):
    
    """
    Traces = LoadTraces(db_file = "../tools/database.db",
                        start = "2019-11-01",
                        end = "2019-11-10")
    """
    
	### Connexion à la base de données
    db = sqlite3.connect(db_file, isolation_level=None)
    
    db.create_function('REGEXP', 2, lambda x, y: 1 if re.search(x,y) else 0)
    
    ### Récupérer les portions mseed dans le range (start, end)
    # (ENDTIME >= start) & (STARTTIME <= end)
    # (   f    >= start) & (    i     <= end)
    #
    #           start                          end
    #             ├─────────────────────────────┤                   input range
    # 
    #  i       fi             fi           fi            fi     f
    #  ├───────┤├─────────────┤├───────────┤├────────────┤├─────┤    all traces
    #
    #      x    ├─────────────┤├───────────┤├────────────┤├─────┤ [1] (f >= start)
    # 
    #  ├───────┤├─────────────┤├───────────┤├────────────┤   x    [2] (i <= end)
    # 
    #      x    ├───── v ─────┤├──── v ────┤├──── v ─────┤   x       [1] & [2]
    #
    
    query = f"""
            SELECT * FROM DATASET
            WHERE
            ENDTIME >= DATETIME('{start}')
            AND
            STARTTIME <= DATETIME('{end}')
            ;
            """
    dfFiles = pd.read_sql_query(query, db)
    db.close()
    
    dfFiles["StationFullName"] = dfFiles.apply(
            lambda row: f"{row.NETWORK}.{row.STATION}.{row.LOCATION}.{row.CHANNEL}",
            axis=1
        )
    stations = list(set(dfFiles["STATION"]))
    
    Stream = read().clear()
    
    for station in stations:
        for comp in config["Components"]:
            
            # Filter station with their code
            channels = list(set(dfFiles.loc[dfFiles["STATION"] == station]["CHANNEL"]))
            channels = [elt for elt in channels if elt[-1] == comp]
            channelSorted = channelSort(channels)
            
            if len(channelSorted) == 0:
                continue
            
            channelGood = channelSorted[0]
            
            dfFilt = dfFiles[
                (dfFiles["STATION"] == station) &
                (dfFiles["CHANNEL"] == channelGood)
            ]
            
            # Filter station with their location code
            dfFilt = dfFilt[
                (dfFilt["LOCATION"] == min(dfFilt["LOCATION"].values))
            ]
            
            # Append to Stream object
            for file in list(dfFilt["FILE"]):
                try:
                    Stream += read(file)
                except:
                    continue
    
    
    
    return Stream
