#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import glob
import numpy as np
from datetime import datetime, timedelta
import pickle as pkl
import shutil
from tqdm import tqdm
from scipy.io import loadmat
from pathlib import Path
from obspy import read_inventory

from multiprocessing import Pool
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed

import sda.functions.config as conf
from sda.functions.stations_define import MakeCouplesOfStation
from sda.xcorr_noise_postprocessing.Stack import Stack
from sda.xcorr_noise_postprocessing.CorrelationsPostProcessing import CorrFilter


def PostProcessingPair(pairs, config):
    sta1 = pairs[0]
    sta2 = pairs[1]
    stack = config["StackDays"]
    
    lagtime = np.arange(-config["Maxlag"] / config["NewFrequence"],
                        config["Maxlag"] / config["NewFrequence"] + 1./config["NewFrequence"],
                        1./config["NewFrequence"])
    
    dayStart = datetime.strptime(config["starttime"], "%Y-%m-%d")
    dayEnd = datetime.strptime(config["endtime"], "%Y-%m-%d")
    NofDays = (dayEnd - dayStart).days
    day_str = [(dayStart + timedelta(days=i)).strftime("%Y/%j") for i in range(NofDays)]
    
    
    ### Loading Data and format with nan gaps
    data = {}
    time = []
    for i in range(len(day_str)):
        
        year = int(day_str[i].split("/")[0])
        doy = int(day_str[i].split("/")[1])
        time.append(datetime(year,1,1) + timedelta(days=doy-1))       
        corr_dict = {}        
        
        for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:
        
            file = os.path.join(config["SaveDirectory"],
                                "{}_CORRC1".format(comp),
                                day_str[i],
                                "{}_CORRC1".format(sta1),
                                "{}_CORRC1_{}.mat".format(sta1,sta2))
            
            
            if not os.path.isfile(file): continue
            
            cur = loadmat(file)
            corr_dict[comp] = cur['corr'][0]
            
        for comp in corr_dict.keys():
            if comp in data : data[comp][:,i] = corr_dict[comp]
            else:             data[comp] = np.zeros( (len(lagtime), len(day_str)) ) * np.nan
            
    time = np.array(time)
        
    for comp in data.keys():
        data_comp = data[comp]
        if np.count_nonzero(~np.isnan(data_comp)) != 0:
            ### Apply PostProcessing and correlations
            if config["doSVDWiener"]:
                try:
                    data_comp = CorrFilter(time, lagtime, data_comp, config)
                except:
                    continue
            
            ### Stacking correlations
            Stack(time, lagtime, data_comp, sta1, sta2, comp, config)



def PostProcessingPoolHandler(pairs, config):
    # Utilisation de ThreadPoolExecutor pour la parallélisation
    with ThreadPoolExecutor(max_workers=config["NumberOfProcesses"]) as executor:
        # Soumission des tâches avec les arguments supplémentaires
        futures = [executor.submit(PostProcessingPair, pair, config) for pair in pairs]
        
        # Utilisation de tqdm pour la barre de progression
        for future in tqdm(as_completed(futures), total=len(futures), desc=datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " PostProcessing  "):
            future.result()
                


def run(
    outputPath,
    starttime,
    endtime,
    NewFrequence,
    Maxlag,
    NumberOfProcesses=1,
    stations = [],
    doSVDWiener = False,
    SVDThreshold = 15,
    WienerFiltTime = 5,
    WienerFiltLagTime = 5,
    StackDays = 10,
    StackOverlap = 0,
    minDays = 1,
):
    SaveDirectory = os.path.join(outputPath, "xcorr_noise")
    SaveDirectoryPostProcess = os.path.join(outputPath, "xcorr_noise_postprocessing")
    
    # Prepare config dictionary
    config = {
        "SaveDirectory" : SaveDirectory,
        "SaveDirectoryPostProcess" : SaveDirectoryPostProcess,
        "starttime" : starttime,
        "endtime" : endtime,
        "NumberOfProcesses": NumberOfProcesses,
        "NewFrequence" : NewFrequence,
        "Maxlag" : Maxlag,
        "stations" : stations,
        "doSVDWiener" : doSVDWiener,
        "SVDThreshold" : SVDThreshold,
        "WienerFiltTime" : WienerFiltTime,
        "WienerFiltLagTime" : WienerFiltLagTime,
        "StackDays" : StackDays,
        "StackOverlap" : StackOverlap,
        "minDays" : minDays
    }
    config = conf.update(config)
             
    pairs = MakeCouplesOfStation(config)
    PostProcessingPoolHandler(pairs, config)
