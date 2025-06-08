import sys
import os
import numpy as np
from datetime import datetime, timedelta
import time
import pickle as pkl



def Stack(time, lagtime, data, sta1, sta2, comp, config):
    
    SaveDirectory = config["SaveDirectoryPostProcess"]
    
    stack_time = np.array(time)
    stack_lagtime = lagtime
    stack_array = data
    StackDay = config["StackDays"]
    notNaN = ~np.isnan(np.sum(stack_array, axis=0))
        
        
    if StackDay == 1:
        StackDict = {
            "array":stack_array[:,notNaN],
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
            "lagtime":stack_lagtime,
            "timeLeft":timeStackBinLeft[notNaN],
            "timeRight":timeStackBinRight[notNaN],
            "timeCenter":timeStackBinCenter[notNaN],
            }
        
    if np.count_nonzero(~np.isnan(StackDict["array"])) != 0:        
        savepath = os.path.join(SaveDirectory,"{:03d}days/{}".format(StackDay, comp))
        filename = os.path.join(savepath,"{}-{}.pkl".format(sta1,sta2))
        
        try:
            os.makedirs(savepath)
        except:
            pass
        
        with open(filename, 'wb') as f:
            pkl.dump(StackDict, f)