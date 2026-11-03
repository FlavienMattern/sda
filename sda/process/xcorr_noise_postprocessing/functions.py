import os
import numpy as np
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
    
    stack_time = np.asarray(time, dtype="datetime64[ns]")
    count = config["StackCount"]
    step = max(1, round(count * (1 - config["StackOverlap"])))
    starts = np.arange(0, len(stack_time) - count + 1, step)
    arrayStack = np.full((len(lagtime), len(starts)), np.nan)
    for j, i in enumerate(starts):
        block = data[:, i:i + count]
        valid = np.isfinite(block).all(axis=0)
        if valid.any():
            arrayStack[:, j] = block[:, valid].mean(axis=1)

    StackDict = {
        "array": arrayStack,
        "fs": fs,
        "lagtime": lagtime,
        "time": stack_time[starts],
    }
    if np.isfinite(arrayStack).any():
        savepath = os.path.join(SaveDirectory, f"stack_{count}", comp)
        filename = os.path.join(savepath,"{}-{}.h5".format(sta1,sta2))
        os.makedirs(savepath, exist_ok=True)
        save_file(filename, StackDict)
    else:
        add_log(f"Not enough data for {sta1}-{sta2} ({comp}). Results not saved.", level="warning")



def save_file(filename, StackDict):

    times = np.asarray(StackDict["time"], dtype="datetime64[ns]").astype("int64")

    with h5py.File(filename, 'w') as f:
        f.create_dataset("array", data=StackDict["array"], compression="gzip", dtype="float32")
        f.create_dataset("fs", data=StackDict["fs"], dtype="float32")
        f.create_dataset("lagtime", data=StackDict["lagtime"], compression="gzip", dtype="float32")
        f.create_dataset("time", data=times)
