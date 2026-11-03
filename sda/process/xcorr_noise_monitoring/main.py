import os
from tqdm import tqdm
import pandas as pd
import numpy as np
from obspy import read_inventory, UTCDateTime
import geopy.distance
from datetime import datetime
from loky.backend import get_context
from functools import partial
import h5py

# Local modules
from sda.process.xcorr_noise_monitoring.MonitoringMethods import stretching, mwcs
from sda.core.stations_define import MakeCouplesOfStation
from sda.core.rotationRTZ import rotationRTZ
from sda.core.logs import add_log, get_worker_logging_config, init_worker_logging
from sda.core.xcorr_noise import load_h5_corr
from sda.core.xcorr_noise_monitoring import save_dvv_results


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
    SaveDirectory = os.path.join(config["outputPath"], "xcorr_noise_monitoring")
    CorrDirectory = os.path.join(config["outputPath"], "xcorr_noise_postprocessing")
    freq_str = f"{freq[0]:.3f}-{freq[1]:.3f}Hz"
    
    start, end = config["starttime"], config["endtime"]
    start_ns = start.ns if isinstance(start, UTCDateTime) else pd.Timestamp(start).value
    end_ns = end.ns if isinstance(end, UTCDateTime) else pd.Timestamp(end).value
    if isinstance(end, str) and len(end) == 10:
        end_ns += 86400 * 1_000_000_000

    # Load data
    sta1 = pairs[0]
    sta2 = pairs[1]
    stack_str = f"stack_{config['StackCount']}"
    
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
    use_velocity = isinstance(config["LagtimeVelocity"], (list, tuple)) or config["LagtimeVelocity"] != 0
    if use_velocity:
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
    
    ### Get xcorr results
    dataZNE = {}
    for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:
        filename = os.path.join(CorrDirectory, stack_str, comp, f"{sta1}-{sta2}.h5")
        if not os.path.exists(filename): continue
        
        data, lagtime, time, metadata = load_h5_corr(filename)
        time = np.asarray(time, dtype="datetime64[ns]")
        selected = (time >= np.datetime64(start_ns, "ns")) & (time < np.datetime64(end_ns, "ns"))
        if not selected.any():
            continue
        
        refstarttime = config["refstarttime"]
        refendtime = config["refendtime"]
        if (refstarttime==None) or (refendtime==None):
            ref = np.nanmean(data, axis=1)
        else:
            ref_start_ns = refstarttime.ns if isinstance(refstarttime, UTCDateTime) else pd.Timestamp(refstarttime).value
            ref_end_ns = refendtime.ns if isinstance(refendtime, UTCDateTime) else pd.Timestamp(refendtime).value
            if isinstance(refendtime, str) and len(refendtime) == 10:
                ref_end_ns += 86400 * 1_000_000_000
            idxref = (time >= np.datetime64(ref_start_ns, "ns")) & (time < np.datetime64(ref_end_ns, "ns"))
            ref = np.nanmean(data[:,idxref], axis=1)

        ### Folding 
        if config["LagtimeSide"] == "fold":
            
            data_fold = np.zeros(np.shape(data))* np.nan
            causal_data = data[int(data.shape[0]/2):,:]
            acausal_data = np.flip(data[:int(data.shape[0]/2)+1,:], axis=0)
            fold_array = (acausal_data + causal_data)/2
            data_fold[int(data_fold.shape[0]/2):,:] = fold_array
            data_fold[:int(data_fold.shape[0]/2)+1,:] = np.flip(fold_array, axis=0)

            middle = len(ref) // 2
            ref_causal = ref[middle:]
            ref_acausal = np.flip(ref[:middle+1])
            ref_fold_array = (ref_causal + ref_acausal)/2
            ref_fold = np.full_like(ref, np.nan)
            ref_fold[middle:] = ref_fold_array
            ref_fold[:middle+1] = np.flip(ref_fold_array)
            
            # Change initial data with the folded version
            data = data_fold
            ref = ref_fold
            
        dataZNE[comp] = {"data": data[:,selected], "ref": ref, "time": time[selected]}
        
    if dataZNE == {}:
        return

    para = {"twin": lagtime, "freq": freq, "dt": 1 / metadata["fs"]}
    if use_velocity:
        max_lag = metadata["max_lag"]
        lagtime_range = [(max(left, -max_lag), min(right, max_lag)) for left, right in lagtime_range]

    results = {"metadata":{"sta1":sta1,"sta2":sta2}, "data":{}}
    if config["doStretching"]:
        results["data"]["stretching"] = {}
    if config["doDoublet"]:
        results["data"]["doublet"] = {}
        
    time = np.unique(np.concatenate([values["time"] for values in dataZNE.values()]))
    
    for instant in time:
        
        time_str = str(instant)
        
        try:
            # Rotation
            corr_dict = {}
            ref_dict  = {}
            for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:
                if comp in dataZNE.keys():
                    cur = dataZNE[comp]["data"][:, dataZNE[comp]["time"]==instant].flatten()
                    ref = dataZNE[comp]["ref"]
                    if cur.size and np.isfinite(cur).all() and np.isfinite(ref).all():
                        corr_dict[comp] = cur
                        ref_dict[comp] = ref
            
            if config["RotationComponents"] is not None:
                if len(config["RotationComponents"]) != 0:
                    corr_dict = rotationRTZ(sta1, sta2, inventory, corr_dict, config["RotationComponents"])
                    ref_dict  = rotationRTZ(sta1, sta2, inventory, ref_dict, config["RotationComponents"])
                
        except Exception as e:
            add_log(f"Error while rotating pair {sta1}-{sta2} at {instant}: {e}", level="error")
            continue

        # Monitoring for all cross-components
        for comp in corr_dict.keys():
            cur = corr_dict[comp]
            ref = ref_dict[comp]
            
            if config["doStretching"]:
                try:
                    stretchingResults = stretching(ref, cur, dv_range, nbtrial, lagtime_range, para)
                    for lag_str, value in stretchingResults.items():
                        if not np.isfinite(value["dv"]):
                            continue
                        # Formatting dictionnary                        
                        res = results["data"]["stretching"].setdefault(freq_str, {}).setdefault(stack_str, {}).setdefault(comp, {}).setdefault(lag_str, {"time":[], "dvv":[], "coherence":[], "error":[]})
                        # Appeding data in dictionnary
                        res["time"].append(time_str)
                        res["dvv"].append(value["dv"])
                        res["coherence"].append(value["cc"])
                        res["error"].append(value["error"])
                except Exception as e:
                    add_log(f"Error while processing pair {sta1}-{sta2} ({comp}) at {instant} (stretching): {e}", level="debug")
                

            if config["doDoublet"]:
                try:
                    doubletResults = mwcs(ref, cur, t_moving_window_length, t_slide_step, para, lagtime_range, smoothing_half_win=5)
                    for lag_str, value in doubletResults.items():
                        if not np.isfinite(value["dv"]):
                            continue
                        # Formatting dictionnary                        
                        res = results["data"]["doublet"].setdefault(freq_str, {}).setdefault(stack_str, {}).setdefault(comp, {}).setdefault(lag_str, {"time":[], "dvv":[], "coherence":[], "error":[]})
                        # Appeding data in dictionnary
                        res["time"].append(time_str)
                        res["dvv"].append(value["dv"])
                        res["coherence"].append(value["cc"])
                        res["error"].append(value["error"])
                except Exception as e:
                    add_log(f"Error while processing pair {sta1}-{sta2} ({comp}) at {instant} (mwcs): {e}", level="debug")
            
        

        # Note : to read the saved 3D DataFrame and use id
        # df = pd.read_csv(filename, index_col=[0], header=[0,1])
        # df.loc[Time Index, Lagtime Bands][Parameters]
        #  > example : df.loc[:, "-20.00_0.00s"]["dv"]
        #    read the [-20, 0]s lagtime band for all timestamps and return dv only
        
        
    if not any(results["data"].values()):
        return
    os.makedirs(SaveDirectory, exist_ok=True)
    filename = os.path.join(SaveDirectory, f"{sta1}-{sta2}.h5")
        
    with h5py.File(filename, "a") as f:
        save_dvv_results(f, results)



def MonitoringPoolHandler(pairs, config, inventory):   
    # We set config dict as a non iterable argument for parallel processing
    MonitoringParallelWithConfig = partial(MonitoringParallel, config=config, inventory=inventory)
    # Create Pool with a progress bar
    with get_context("loky").Pool(processes=config["NumberOfProcesses"], initializer=init_worker_logging,
              initargs=get_worker_logging_config()) as p:
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
    refstarttime = None,
    refendtime = None,
    StackCount = 1,
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
        "StackCount" : StackCount,
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
    add_log("Configuration parameters:", level="info")
    for key in config:
        add_log(f"  - {key} : {config[key]}", level="info")

    # Read inventory file
    inventory = None
    if (config["LagtimeVelocity"] != 0) or config["RotationComponents"] or (config["maxInterDistance"] is not None):
        for path, _, files in os.walk(config['inventory_path']):
            for name in files:
                if name[-4:] == ".xml":
                    invfile = os.path.join(path, name)
                    inv = read_inventory(invfile, format="STATIONXML")
                    if inventory is None:
                        inventory = inv
                    else:
                        inventory.extend(inv)

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

        
