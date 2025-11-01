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
    C_nonan = C[:,idxGood]
    Cfull = np.zeros(np.shape(C_nonan))
    
    for j in range(1):
        U, Sval, Vt = np.linalg.svd(C_nonan, full_matrices=True)
        
        for i in range(threshold):
            # SVD Decomposition for singular value i
            S = np.zeros(np.shape(Cfull))
            S[i, i] = Sval[i]
            C = U.dot(S).dot(Vt)
            
            # SVD Wiener
            C = scipy.signal.wiener(C, (L, K))
            
            Cfull += C
            
        C_nonan = Cfull.copy()
                
    Cfull = scipy.signal.wiener(Cfull, (L, K))
    
    dataFilt = np.zeros( (len(lagtime), len(time)) ) * np.nan
    dataFilt[:,idxGood] = Cfull
    
    return dataFilt