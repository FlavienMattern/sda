#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
from scipy.io import loadmat
import pandas as pd

from multiprocessing import Pool
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed

import sda.core.config as conf
from sda.core.stations_define import MakeCouplesOfStation
from sda.process.xcorr_noise_postprocessing.functions import Stack, CorrFilter
from sda.core.logs import add_log
from sda.core.xcorr_noise import load_h5_corr
import traceback


def PostProcessingPair(pairs, config):
    sta1 = pairs[0]
    sta2 = pairs[1]
    
    dayStart = datetime.strptime(config["starttime"], "%Y-%m-%d")
    dayEnd   = datetime.strptime(config["endtime"], "%Y-%m-%d")
    full_times = pd.date_range(start=dayStart, end=dayEnd, freq="D")

    data = {}
    for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:

        file = os.path.join(config["SaveDirectory"], comp, f"{sta1}-{sta2}.h5")
        if not os.path.isfile(file): continue
        xcorr, lagtime, times, fs = load_h5_corr(file)
        xcorr = xcorr.T

        df = pd.DataFrame(xcorr, index=times, columns=lagtime)
        df = df.reindex(index=full_times)
        xcorr = df.values
        data[comp] = xcorr.T

    time = full_times.to_pydatetime()
        
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
            Stack(time, lagtime, data_comp, sta1, sta2, comp, config, fs)


def xcorr_noise_postprocessing(
    outputPath,
    starttime,
    endtime,
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

    # Run in multiprocessing
    PostProcessingParallelWithConfig = partial(PostProcessingPair, config=config)
    with Pool(processes=config["NumberOfProcesses"]) as p:
        with tqdm(total=len(pairs), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " PostProcessing  ")
            for _ in p.imap_unordered(PostProcessingParallelWithConfig, pairs):
                pbar.update()

    add_log("End process: xcorr_noise_postprocessing", level="info")
    add_log("#"*50, level="info")