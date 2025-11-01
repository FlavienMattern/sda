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

import sda.core.config as conf
from sda.core.stations_define import MakeCouplesOfStation
from sda.process.xcorr_noise_postprocessing.CorrelationsPostProcessing import CorrFilter
from sda.process.xcorr_noise_postprocessing.Stack import Stack
from sda.core.logs import add_log

import traceback


def PostProcessingPair(pairs, config):
    sta1 = pairs[0]
    sta2 = pairs[1]
    
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

        # TODO : 
        # Maxlag = max(abs(lag)) dans le vecteur temps de la corrélation
        # NewFrequence = len(lag) / Maxlag (ou len(lag)+1) ?
        # comme ça pas besoin de les mettre en input
        if "lagtime" not in locals():
            lagtime = np.arange(-config["Maxlag"] / config["NewFrequence"],
                                config["Maxlag"] / config["NewFrequence"] + 1./config["NewFrequence"],
                                1./config["NewFrequence"])
            
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
                    msg = f"An error occurred while applying SVD-Wiener on pair {sta1}-{sta2}. Skipping pair.\n"
                    msg += traceback.format_exc()
                    add_log(msg, level="error")
                    continue
            
            ### Stacking correlations
            Stack(time, lagtime, data_comp, sta1, sta2, comp, config)



def PostProcessingPoolHandler(pairs, config):
    with ThreadPoolExecutor(max_workers=config["NumberOfProcesses"]) as executor:
        futures = [executor.submit(PostProcessingPair, pair, config) for pair in pairs]
        for future in tqdm(as_completed(futures), total=len(futures), desc=datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " PostProcessing  "):
            future.result()
                


def xcorr_noise_postprocessing(
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
    """_summary_

    Args:
        outputPath (_type_): _description_
        starttime (_type_): _description_
        endtime (_type_): _description_
        NewFrequence (_type_): _description_
        Maxlag (_type_): _description_
        NumberOfProcesses (int, optional): _description_. Defaults to 1.
        stations (list, optional): _description_. Defaults to [].
        doSVDWiener (bool, optional): _description_. Defaults to False.
        SVDThreshold (int, optional): _description_. Defaults to 15.
        WienerFiltTime (int, optional): _description_. Defaults to 5.
        WienerFiltLagTime (int, optional): _description_. Defaults to 5.
        StackDays (int, optional): _description_. Defaults to 10.
        StackOverlap (int, optional): _description_. Defaults to 0.
        minDays (int, optional): _description_. Defaults to 1.
    """

    add_log("#"*50, level="info")
    add_log("Start process: xcorr_noise_postprocessing", level="info")

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
    add_log("Configuration parameters:", level="info")
    for key in config:
        add_log(f"  - {key} : {config[key]}", level="info")
             
    pairs = MakeCouplesOfStation(config)
    add_log("Starting postprocessing of ambient noise correlations...", level="info")
    PostProcessingPoolHandler(pairs, config)

    add_log("End process: xcorr_noise_postprocessing", level="info")
    add_log("#"*50, level="info")