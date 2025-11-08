import sys
import os
import numpy as np
from datetime import datetime, timedelta
import time
import pickle as pkl
import scipy.signal
import matplotlib.pyplot as plt



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