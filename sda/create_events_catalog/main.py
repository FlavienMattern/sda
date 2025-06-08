import os
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm
from datetime import datetime
import time
import matplotlib.pyplot as plt

# Fonctions OBSPY
from obspy import read_inventory
from obspy.core import UTCDateTime

# SDA methods
from sda.create_events_catalog.catalog_functions import LoadTraces, PreProcessTrace


import warnings
warnings.filterwarnings("ignore")



def CatalogParallel(t0, config, inventory):
    start = (t0 + config["starttimeEvent"]).strftime("%Y-%m-%d %H:%M:%S.%f")
    end   = (t0 + config["endtimeEvent"]).strftime("%Y-%m-%d %H:%M:%S.%f")
    Stream = LoadTraces(os.path.join(config["outputPath"], "database.db"), config, start, end)
    # Cut data
    Stream.trim(starttime=UTCDateTime(start), endtime=UTCDateTime(end))

    for Trace in Stream:

        stationName = f"{Trace.stats.station}_{Trace.stats.channel[-1]}"
        
        # Preprocessing step
        Trace = PreProcessTrace(Trace, t0, inventory, config)

        # Process Trace
        # try:
        #     Trace = ProcessBeforeCodaSelect(Trace, t0, inventory, config)
        # except:
        #     continue

        # STA/LTA
        # try:
        #     trigON, trigOFF = sta_lta(Trace, config)
        # except:
        #     continue
        # Trace.trim(starttime=Trace.stats.starttime + trigON,
        #         endtime=Trace.stats.starttime + trigOFF)

        # Saving Trace
        SaveFolder = os.path.join(config["outputPath"], "events_catalog", t0.strftime("%Y%m%d_%H%M%S.%f"))
        try:
            os.makedirs(SaveFolder)
        except:
            pass

        Trace.write(os.path.join(SaveFolder, f"{stationName}.mseed"), format="MSEED")



def CatalogPoolHandler(t0Events, config, inventory):   
    # We set config dict as a non iterable argument for parallel processing
    CatalogParallelWithConfig = partial(CatalogParallel, config=config, inventory=inventory)
    # Create Pool with a progress bar
    with Pool(processes=config["NumberOfProcesses"]) as p:
        with tqdm(total=len(t0Events)) as pbar:
            for _ in p.imap_unordered(CatalogParallelWithConfig, t0Events):
                pbar.update()




def run(
    outputPath,
    eventsPath,
    databasePath = None,
    inventory_path = None,
    DataPath = None,
    stations = [],
    NumberOfProcesses = 1,
    lenSTA = 2,
    lenLTA = 5,
    triggerHigh = 2,
    triggerLow = 1,
    starttimeEvent = -20, # [s] Start time from Origin time (neg. value is before t0, pos. value is after t0)
    endtimeEvent = 60, # [s] End time from Origin time (neg. value is before t0, pos. value is after t0)
    Components = ["Z", "N", "E"],
    remove_response = True,
    water_level = 60,
    response_prefilt = (0.05, 0.06, 7.0, 9.0),
    freqMin = 0.1,
    freqMax = 5,
    NewFrequence = 20
    ):
    
    config = {
        "outputPath": outputPath,
        "eventsPath": eventsPath,
        "databasePath": databasePath,
        "inventory_path": inventory_path,
        "DataPath": DataPath,
        "stations": stations,
        "NumberOfProcesses": NumberOfProcesses,
        "lenSTA": lenSTA,
        "lenLTA": lenLTA,
        "triggerHigh": triggerHigh,
        "triggerLow": triggerLow,
        "starttimeEvent": starttimeEvent,
        "endtimeEvent": endtimeEvent,
        "Components": Components,
        "remove_response": remove_response,
        "water_level": water_level,
        "response_prefilt": response_prefilt,
        "freqMin": freqMin,
        "freqMax": freqMax,
        "NewFrequence": NewFrequence
    }
    
    fileEvents = open(eventsPath, "r").read().split('\n')
    t0Events = []
    for t0 in fileEvents:
        try:
            t0Events.append(UTCDateTime(t0))
        except:
            continue
        
    for path, subdirs, files in os.walk(inventory_path):
        for name in files:
            if name[-4:] == ".xml":
                invfile = os.path.join(path, name)
                inv = read_inventory(invfile, format="STATIONXML")
                try:
                    inventory.extend(inv)
                except NameError:
                    inventory = inv
                    
    # Lancement du multiprocessing
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), end=" ")
    print("Creating catalog of wavefroms with {} processes.".format(config["NumberOfProcesses"]))
    t = time.time()
    CatalogPoolHandler(t0Events, config, inventory)
    delay = time.time() - t
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), end=" ")
    print("Done. ({}) seconds".format(round(delay,2)))

