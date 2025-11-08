import sys
import os
import numpy as np
from datetime import datetime, timedelta
import time
import pickle as pkl
from sda.core.logs import add_log
import h5py
import scipy.signal



def CorrFilter(time, lagtime, data, config):
    
    threshold = config["SVDThreshold"]
    K = config["WienerFiltTime"] # Wiener window in date dimension (smoothing of K days)
    L = config["WienerFiltLagTime"] # Wiener window in lag time dimension (1/L * fs = lag time smoothing)
    C = data
    idxGood = ~np.all(np.isnan(C), axis=0)
    C_nonan = C[:, idxGood]

    # SVD
    U, Sval, Vt = np.linalg.svd(C_nonan, full_matrices=False)
    U = U[:, :threshold]
    Sval = Sval[:threshold]
    Vt = Vt[:threshold, :]

    # Wiener filter
    Cfull = np.zeros_like(C_nonan)
    for i in range(threshold):
        Ci = np.outer(U[:, i], Vt[i, :]) * Sval[i]
        Ci = scipy.signal.wiener(Ci, (L, K))
        Cfull += Ci

    Cfull = scipy.signal.wiener(Cfull, (L, K))

    # Reconstruct matrix
    dataFilt = np.full((len(lagtime), len(time)), np.nan)
    dataFilt[:, idxGood] = Cfull
    
    return dataFilt



def Stack(time, lagtime, data, sta1, sta2, comp, config, fs):
    
    SaveDirectory = config["SaveDirectoryPostProcess"]
    
    stack_time = np.array(time)
    stack_lagtime = lagtime
    stack_array = data
    StackDay = config["StackDays"]
    notNaN = ~np.isnan(np.sum(stack_array, axis=0))
        
        
    if StackDay == 1:
        StackDict = {
            "array":stack_array[:,notNaN],
            "fs":fs,
            "lagtime":stack_lagtime,
            "timeLeft":stack_time[notNaN],
            "timeRight":stack_time[notNaN],
            "timeCenter":stack_time[notNaN],
            }
    else:
        ### Stack data with multiple days    
        istart = min(stack_time)
        iend = istart + timedelta(days=StackDay)
        imiddle = istart + timedelta(days=int(StackDay/2))  
        timeStackBinLeft = []
        timeStackBinRight = []
        timeStackBinCenter = []
        while iend <= max(time):
            timeStackBinLeft.append(istart)
            timeStackBinRight.append(iend)
            timeStackBinCenter.append(imiddle)
            istart += timedelta(days=int(StackDay*(1-config["StackOverlap"])))
            iend  = istart + timedelta(days=StackDay)   
            imiddle = istart + timedelta(days=int(StackDay/2))  
            
        timeStackBinLeft = np.asarray(timeStackBinLeft)
        timeStackBinRight = np.asarray(timeStackBinRight)
        timeStackBinCenter = np.asarray(timeStackBinCenter)
        
        arrayStack = np.zeros( (len(stack_lagtime), len(timeStackBinLeft)) ) * np.nan
        for i in range(len(timeStackBinLeft)):
            istart = timeStackBinLeft[i]
            iend = timeStackBinRight[i]
            idx1 = np.where(stack_time >= istart)
            idx2 = np.where(stack_time < iend)
            idx = np.intersect1d(idx1, idx2)

            if len(idx) == 0:
                cur = np.zeros(len(stack_lagtime)) * np.nan
            else:
                cur = np.nanmean(stack_array[:,idx], axis=1)
            
            arrayStack[:,i] = cur
            
        notNaN = ~np.isnan(np.sum(arrayStack, axis=0))
            
        StackDict = {
            "array":arrayStack[:,notNaN],
            "fs":fs,
            "lagtime":stack_lagtime,
            "timeLeft":timeStackBinLeft[notNaN],
            "timeRight":timeStackBinRight[notNaN],
            "timeCenter":timeStackBinCenter[notNaN],
            }
        
    if np.count_nonzero(~np.isnan(StackDict["array"])) != 0:        
        savepath = os.path.join(SaveDirectory,"{:03d}days/{}".format(StackDay, comp))
        filename = os.path.join(savepath,"{}-{}.h5".format(sta1,sta2))
        os.makedirs(savepath, exist_ok=True)
        save_file(filename, StackDict)
    else:
        add_log(f"Not enough data for {sta1}-{sta2} ({comp}). Results not saved.", level="warning")



def save_file(filename, StackDict):

    timeCenter = StackDict["timeCenter"]
    timeCenter = np.array([str(v) for v in timeCenter.astype('datetime64[s]').astype(str)], dtype=h5py.string_dtype())

    with h5py.File(filename, 'w') as f:
        f.create_dataset("array", data=StackDict["array"], compression="gzip", dtype="float32")
        f.create_dataset("fs", data=StackDict["fs"], dtype="float32")
        f.create_dataset("lagtime", data=StackDict["lagtime"], compression="gzip", dtype="float32")
        f.create_dataset("time", data=timeCenter)