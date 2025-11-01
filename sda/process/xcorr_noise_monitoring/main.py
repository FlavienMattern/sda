import pickle as pkl
import os
import sys
from tqdm import tqdm
import pandas as pd
import numpy as np
from obspy import read_inventory
import geopy.distance
from datetime import datetime, timedelta
import time
from multiprocessing import Pool
from functools import partial

# Local modules
from sda.process.xcorr_noise_monitoring.MonitoringMethods import stretching, mwcs
from sda.core.stations_define import MakeCouplesOfStation
from sda.core.rotationRTZ import rotationRTZ
import sda.core.config as conf
from sda.core.logs import add_log
import traceback


###
### Functions to run Correlation and preprocessing in parallel
###
def MonitoringParallel(pairs, config, inventory):
    # Load variables
    lagtime_range = config["LagtimeMonitoring"]
    dv_range = config["StretchingMax"]
    nbtrial = config["StretchingNbTrial"]
    t_moving_window_length = config["DoubletWindowLength"] # [s] Durée de la fenêtre glissante pour le calcul de dt
    t_slide_step = config["DoubletWindowStep"] # [s] Décalage de la fenêtre glissante pour le calcul de dt
    freq = (config["freqMinMonitoring"],config["freqMaxMonitoring"]) # [Hz] Frequency band to compute phase regression
    dt = 1/config["NewFrequence"]
    SaveDirectory = os.path.join(config["outputPath"], "xcorr_noise_monitoring")
    CorrDirectory = os.path.join(config["outputPath"], "xcorr_noise_postprocessing")
    
    dayStart = datetime.strptime(config["starttime"], "%Y-%m-%d")
    dayEnd = datetime.strptime(config["endtime"], "%Y-%m-%d")
    NofDays = (dayEnd - dayStart).days
    dates = [(dayStart + timedelta(days=i)) for i in range(NofDays)]

    # Load data
    sta1 = pairs[0]
    sta2 = pairs[1]
    stack_day = "{:03d}".format(config["StackDays"])
    
    if config['maxInterDistance'] != None:
        inv1 = inventory.select(station=sta1)[0][0]
        lat1 = inv1.latitude
        lon1 = inv1.longitude

        inv2 = inventory.select(station=sta2)[0][0]
        lat2 = inv2.latitude
        lon2 = inv2.longitude
        
        dist = geopy.distance.geodesic((lat1,lon1), (lat2,lon2)).km
        
        # Skip if distance inter station is too high
        if dist > config['maxInterDistance']:
            return

    # Define lagtime range with interstation distance
    if (config["LagtimeVelocity"] != 0) or (type(config["LagtimeVelocity"]) == type(list())) or (type(config["LagtimeVelocity"]) == type(tuple())):
        inv1 = inventory.select(station=sta1)[0][0]
        lat1 = inv1.latitude
        lon1 = inv1.longitude

        inv2 = inventory.select(station=sta2)[0][0]
        lat2 = inv2.latitude
        lon2 = inv2.longitude

        dist = geopy.distance.geodesic((lat1,lon1), (lat2,lon2)).km
        
        if (type(config["LagtimeVelocity"]) != type(list())) and (type(config["LagtimeVelocity"]) != type(tuple())):
            lag_velocity = [config["LagtimeVelocity"]]
            lag_shift = [config["LagtimeShift"]]
            lag_window = [config["LagtimeWindowLength"]]
        else:
            lag_velocity = config["LagtimeVelocity"]
            lag_shift = config["LagtimeShift"]
            lag_window = config["LagtimeWindowLength"]

        lagtime_range = []
        
        for i in range(len(lag_velocity)):
            if lag_velocity[i] == 0:
                lagStart = lag_shift[i]
            else:
                lagStart = dist/lag_velocity[i] + lag_shift[i]
                
            if lagStart < 0:
                lagStart = 0
            
            lagEnd = lagStart + lag_window[i]
            
            if lagEnd > config["Maxlag"]:
                lagEnd = config["Maxlag"]

            if config["LagtimeSide"] == "both":
                lagtime_range += [(lagStart, lagEnd), (-lagEnd, -lagStart)]
            elif config["LagtimeSide"] == "causal":
                lagtime_range += [(lagStart, lagEnd)]
            elif config["LagtimeSide"] == "acausal":
                lagtime_range += [(-lagEnd, -lagStart)]
            elif config["LagtimeSide"] == "fold":
                lagtime_range += [(lagStart, lagEnd)]
            else:
                lagtime_range += [(lagStart, lagEnd)]
    
    ### Construct time arrays
    istart = min(dates)
    iend = istart + timedelta(days=int(stack_day))
    imiddle = istart + timedelta(days=int(int(stack_day)/2))  
    timeStackBinLeft = []
    timeStackBinRight = []
    timeStackBinCenter = []
    while iend <= max(dates):
        timeStackBinLeft.append(istart)
        timeStackBinRight.append(iend)
        timeStackBinCenter.append(imiddle)
        istart += timedelta(days=int(int(stack_day)*(1-config["StackOverlap"])))
        iend  = istart + timedelta(days=int(stack_day))   
        imiddle = istart + timedelta(days=int(int(stack_day)/2))

    ### Get xcorr results
    dataZNE = {}
    for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:
        filename = os.path.join(CorrDirectory, f"{stack_day}days", comp, f"{sta1}-{sta2}.pkl")
        
        if not os.path.exists(filename): continue
        
        try:
            with open(filename, 'rb') as f:
                StackDict = pkl.load(f)
        except:
            continue
        data = StackDict["array"]
        lagtime = StackDict["lagtime"]
        time = StackDict["timeCenter"]
        
        refstarttime = config["refstarttime"]
        refendtime = config["refendtime"]
        if (refstarttime==None) or (refendtime==None):
            ref = np.nanmean(data, axis=1)
        else:
            idxref = (time >= datetime.strptime(refstarttime, "%Y-%m-%d")) \
                & (time <= datetime.strptime(refendtime, "%Y-%m-%d"))
            ref = np.nanmean(data[:,idxref], axis=1)

        ### Folding 
        if config["LagtimeSide"] == "fold":
            
            data_fold = np.zeros(np.shape(data))* np.nan
            causal_data = data[int(data.shape[0]/2):,:]
            acausal_data = np.flip(data[:int(data.shape[0]/2)+1,:], axis=0)
            fold_array = (acausal_data + causal_data)/2
            data_fold[int(data_fold.shape[0]/2):,:] = fold_array
            data_fold[:int(data_fold.shape[0]/2)+1,:] = np.flip(fold_array, axis=0)

            ref_causal = ref[len(ref)/2:,:]
            ref_acausal = np.flip(ref[:(len(ref)/2)+1,:])
            ref_fold_array = (ref_causal + ref_acausal)/2
            ref_fold = np.zeros(ref) * np.nan
            ref_fold[len(ref)/2:,:] = ref_fold_array
            data_fold[:(len(ref)/2)+1,:] = np.flip(ref_fold_array, axis=0)
            
            # Change initial data with the folded version
            data = data_fold
            ref = ref_fold
            
        dataZNE[comp] = {"data":data, "ref":ref, "time":time}

    # Parameters for functions
    lagtime = np.arange(-config["Maxlag"] / config["NewFrequence"],
                        config["Maxlag"] / config["NewFrequence"] + 1./config["NewFrequence"],
                        1./config["NewFrequence"])
    para={
        "twin":lagtime,
        "freq":freq,
        "dt":dt
        }
    
    if config["doStretching"]: stretchingDataFrame = {}
    if config["doDoublet"]:    doubletDataFrame = {}
     
    try:
        time = StackDict["timeCenter"]
    except:
        return
    
    # for idx, day in enumerate(timeStackBinCenter):
    for idx, day in enumerate(time):
        try:
            # Rotation
            corr_dict = {}
            ref_dict  = {}
            for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:
                if comp in dataZNE.keys():
                    corr_dict[comp] = dataZNE[comp]["data"][:, dataZNE[comp]["time"]==day].flatten()
                    ref_dict[comp]  = dataZNE[comp]["ref"]
            
            if len(config["RotationComponents"]) != 0:
                corr_dict = rotationRTZ(sta1, sta2, inventory, corr_dict, config["RotationComponents"])
                ref_dict  = rotationRTZ(sta1, sta2, inventory, ref_dict, config["RotationComponents"])

            # Monitoring for all cross-components
            for comp in corr_dict.keys():
                cur = corr_dict[comp]
                ref = ref_dict[comp]

                if config["doStretching"]:
                    stretchingResults = stretching(ref, cur, dv_range, nbtrial, lagtime_range, para)
                    HEADER_names = list(stretchingResults.keys())
                    SUBHEADER_names = list(stretchingResults[list(stretchingResults.keys())[0]].keys())
                    SUBHEADER = np.array(SUBHEADER_names*len(stretchingResults))
                    HEADER = np.array([[HEADER_names[i]]*len(SUBHEADER_names) for i in range(len(HEADER_names))]).flatten()
                    VALUES = np.array([[stretchingResults[l][m]] for l in stretchingResults.keys() for m in stretchingResults[l].keys()])
                    stretchingResults = pd.DataFrame(data=VALUES.T, columns=pd.MultiIndex.from_tuples(zip(HEADER,SUBHEADER)))
                    stretchingResults = stretchingResults.set_index(pd.to_datetime(np.array([time[idx]]), format="%Y-%m-%d"))
                    if comp not in stretchingDataFrame: stretchingDataFrame[comp] = pd.DataFrame()
                    stretchingDataFrame[comp] = pd.concat([stretchingDataFrame[comp], stretchingResults])

                if config["doDoublet"]:
                    doubletResults = mwcs(ref, cur, t_moving_window_length, t_slide_step, para, lagtime_range, smoothing_half_win=5)
                    HEADER_names = list(doubletResults.keys())
                    SUBHEADER_names = list(doubletResults[list(doubletResults.keys())[0]].keys())
                    SUBHEADER = np.array(SUBHEADER_names*len(doubletResults))
                    HEADER = np.array([[HEADER_names[i]]*len(SUBHEADER_names) for i in range(len(HEADER_names))]).flatten()
                    VALUES = np.array([[doubletResults[l][m]] for l in doubletResults.keys() for m in doubletResults[l].keys()])
                    doubletResults = pd.DataFrame(data=VALUES.T, columns=pd.MultiIndex.from_tuples(zip(HEADER,SUBHEADER)))
                    doubletResults = doubletResults.set_index(pd.to_datetime(np.array([time[idx]]), format="%Y-%m-%d"))
                    if comp not in doubletDataFrame: doubletDataFrame[comp] = pd.DataFrame()
                    doubletDataFrame[comp] = pd.concat([doubletDataFrame[comp], doubletResults])
        except Exception as e:
            print(e)
            continue
            

        if config["doStretching"]:
            for comp in stretchingDataFrame.keys():
                SaveFolderStretching = os.path.join(SaveDirectory, "Stretching/{:.2f}-{:.2f}Hz/{:03d}days/{}".format(min(freq), max(freq), int(stack_day), comp))
                SaveFilenameStretching = os.path.join(SaveFolderStretching, "{}-{}.csv".format(sta1,sta2))
                try:
                    os.makedirs(SaveFolderStretching)
                except:
                    pass
                stretchingDataFrame[comp].to_csv(SaveFilenameStretching)
        
        if config["doDoublet"]:
            for comp in doubletDataFrame.keys():
                SaveFolderDoublet = os.path.join(SaveDirectory, "Doublet/{:.2f}-{:.2f}Hz/{:03d}days/{}".format(min(freq), max(freq), int(stack_day), comp))
                SaveFilenameDoublet = os.path.join(SaveFolderDoublet, "{}-{}.csv".format(sta1,sta2))
                try:
                    os.makedirs(SaveFolderDoublet)
                except:
                    pass
                doubletDataFrame[comp].to_csv(SaveFilenameDoublet)

        # Note : to read the saved 3D DataFrame and use id
        # df = pd.read_csv(filename, index_col=[0], header=[0,1])
        # df.loc[Time Index, Lagtime Bands][Parameters]
        #  > example : df.loc[:, "-20.00_0.00s"]["dv"]
        #    read the [-20, 0]s lagtime band for all days and return dv only




def MonitoringPoolHandler(pairs, config, inventory):   
    # We set config dict as a non iterable argument for parallel processing
    MonitoringParallelWithConfig = partial(MonitoringParallel, config=config, inventory=inventory)
    # Create Pool with a progress bar
    with Pool(processes=config["NumberOfProcesses"]) as p:
        with tqdm(total=len(pairs), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Monitoring      ")
            for _ in p.imap_unordered(MonitoringParallelWithConfig, pairs):
                pbar.update()



###
### Main Programm
###

def xcorr_noise_monitoring(
    outputPath,
    starttime,
    endtime,
    NumberOfProcesses,
    Maxlag,
    NewFrequence,
    refstarttime = None,
    refendtime = None,
    StackDays = 10,
    StackOverlap = 0,
    stations = [],
    inventory_path = None,
    freqMinMonitoring = 1,
    freqMaxMonitoring = 4,
    RotationComponents = ["ZZ"],
    LagtimeMonitoring = [(0,20)],
    LagtimeVelocity = 0,
    LagtimeShift = 0,
    LagtimeWindowLength = 50,
    LagtimeSide = None,
    maxInterDistance=None,
    doStretching = True,
    StretchingMax = 0.06,
    StretchingNbTrial = 100,
    doDoublet = False,
    DoubletWindowLength = 10,
    DoubletWindowStep = 5
):
    
    add_log("#"*50, level="info")
    add_log("Start process: xcorr_noise_monitoring", level="info")
    
    if inventory_path == None:
        inventory_path = os.path.join(outputPath, "data", "inventory")    
    SaveDirectory = os.path.join(outputPath, "xcorr_noise")
    
    # Prepare config dictionary
    config = {
        "outputPath" : outputPath,
        "SaveDirectory" : SaveDirectory,
        "inventory_path" : inventory_path,
        "starttime" : starttime,
        "endtime" : endtime,
        "refstarttime" : refstarttime,
        "refendtime" : refendtime,
        "NumberOfProcesses": NumberOfProcesses,
        "NewFrequence" : NewFrequence,
        "Maxlag" : Maxlag,
        "StackDays" : StackDays,
        "StackOverlap" : StackOverlap,
        "stations" : stations,
        "freqMinMonitoring" : freqMinMonitoring,
        "freqMaxMonitoring" : freqMaxMonitoring,
        "RotationComponents" : RotationComponents,
        "LagtimeMonitoring" : LagtimeMonitoring,
        "LagtimeVelocity" : LagtimeVelocity,
        "LagtimeShift" : LagtimeShift,
        "LagtimeWindowLength" : LagtimeWindowLength,
        "LagtimeSide" : LagtimeSide,
        "maxInterDistance": maxInterDistance,
        "doStretching" : doStretching,
        "StretchingMax" : StretchingMax,
        "StretchingNbTrial" : StretchingNbTrial,
        "doDoublet" : doDoublet,
        "DoubletWindowLength" : DoubletWindowLength,
        "DoubletWindowStep" : DoubletWindowStep
    }
    config = conf.update(config)
    add_log("Configuration parameters:", level="info")
    for key in config:
        add_log(f"  - {key} : {config[key]}", level="info")

    # Read inventory file
    if (config["LagtimeVelocity"] != 0) or (len(config["RotationComponents"]) != 0):
        for path, _, files in os.walk(config['inventory_path']):
            for name in files:
                if name[-4:] == ".xml":
                    invfile = os.path.join(path, name)
                    inv = read_inventory(invfile, format="STATIONXML")
                    try:
                        inventory.extend(inv)
                    except NameError:
                        inventory = inv
    else:
        inventory = None

    os.makedirs(SaveDirectory, exist_ok=True)
    
    # Preparing inputs    
    couples = MakeCouplesOfStation(config)
    pairs = []
    for couple in couples:
        if len(config["stations"]) == 0:
            pair = (couple[0], couple[1])
            if pair not in pairs : pairs.append(pair)
        else:
            if (couple[0] in config["stations"]) and (couple[1] in config["stations"]):
                pair = (couple[0], couple[1])
                if pair not in pairs : pairs.append(pair)
                      
    # Launching monitoring
    add_log("Starting ambient noise monitoring...", level="info")
    MonitoringPoolHandler(pairs, config, inventory)

    add_log("End process: xcorr_noise_monitoring", level="info")
    add_log("#"*50, level="info")

        