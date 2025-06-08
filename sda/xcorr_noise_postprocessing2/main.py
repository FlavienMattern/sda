#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

import sda.functions.config as conf
from sda.functions.stations_define import MakeCouplesOfStation
from sda.xcorr_noise_postprocessing2.Stack import Stack
from sda.xcorr_noise_postprocessing2.CorrelationsPostProcessing import CorrFilter


def PostProcessingPair(pairs, config):
    sta1 = pairs[0]
    sta2 = pairs[1]   
    
    for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:
        folder = os.path.split(config["SaveDirectory"])[0]
        filename = os.path.join(folder, comp, f"{sta1}-{sta2}.csv")
        if not os.path.isfile(filename): continue
        df = pd.read_csv(filename, index_col=0)
        df = df.sort_index()
        data = df.values.T
        lagtime = np.array(df.columns.astype(float))
        time = [datetime(d.year, d.month, d.day) for d in list(pd.to_datetime(df.index))]
        
        
        if len(df) != 0:
            ### Apply PostProcessing and correlations
            if config["doSVDWiener"]:
                try:
                    data = CorrFilter(time, lagtime, data, config)
                except:
                    continue
            
            ### Stacking correlations
            Stack(time, lagtime, data, sta1, sta2, comp, config)



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
