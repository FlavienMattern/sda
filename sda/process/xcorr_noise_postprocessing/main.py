#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import numpy as np
from datetime import datetime
from tqdm import tqdm
import pandas as pd
from obspy import UTCDateTime

from loky.backend import get_context
from functools import partial
from sda.core.stations_define import MakeCouplesOfStation
from sda.process.xcorr_noise_postprocessing.functions import Stack, CorrFilter
from sda.core.logs import add_log, get_worker_logging_config, init_worker_logging
from sda.core.xcorr_noise import load_h5_corr
import traceback


def PostProcessingPair(pairs, config):
    sta1 = pairs[0]
    sta2 = pairs[1]
    
    start, end = config["starttime"], config["endtime"]
    start_ns = start.ns if isinstance(start, UTCDateTime) else pd.Timestamp(start).value
    end_ns = end.ns if isinstance(end, UTCDateTime) else pd.Timestamp(end).value
    if isinstance(end, str) and len(end) == 10:
        end_ns += 86400 * 1_000_000_000
    for comp in ["ZZ", "ZN", "ZE", "NZ", "NN", "NE", "EZ", "EN", "EE"]:

        file = os.path.join(config["SaveDirectory"], comp, f"{sta1}-{sta2}.h5")
        if not os.path.isfile(file): continue
        xcorr, lagtime, times, metadata = load_h5_corr(file)
        fs = metadata["fs"]
        times = np.asarray(times, dtype="datetime64[ns]")
        selected = (times >= np.datetime64(start_ns, "ns")) & (times < np.datetime64(end_ns, "ns"))
        times, data_comp = times[selected], xcorr[:, selected]
        if np.isfinite(data_comp).any():
            ### Apply PostProcessing and correlations
            if config["doSVDWiener"]:
                try:
                    data_comp = CorrFilter(times, lagtime, data_comp, config)
                except:
                    msg = f"An error occurred while applying SVD-Wiener on pair {sta1}-{sta2}. Skipping pair.\n"
                    msg += traceback.format_exc()
                    add_log(msg, level="error")
                    continue
            
            ### Stacking correlations
            Stack(times, lagtime, data_comp, sta1, sta2, comp, config, fs)


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
    StackCount = 10,
    StackOverlap = 0,
):

    """Denoise correlation functions using an SVD-Wiener filter and/or stack correlation functions.
    Read outputs from `<outputPath>/xcorr_noise` and write HDF5 stacks to
    `<outputPath>/xcorr_noise_postprocessing/stack_<StackCount>/<component>/<sta1>-<sta2>.h5`.

    Parameters:
        outputPath (str): Project directory containing the `xcorr_noise` outputs.
        starttime (str | UTCDateTime): UTC start for selecting correlation
            timestamps to monitor, e.g. `"2023-02-01"`, `"2023-02-01T15:00:00"`.
        endtime (str | UTCDateTime): UTC end for selecting correlation
            timestamps to monitor, e.g. `"2023-02-02"`, `"2023-02-02T00:00:00"`.
        NumberOfProcesses (int): Number of worker processes, distributed across station pairs.
        stations (list[str]): Station codes to include, e.g. `["ST01", "ST02"]`.
            An empty list considers all available stations.
        doSVDWiener (bool): Apply an SVD-Wiener filter.
        SVDThreshold (int): Number of singular components to retain. Used with `doSVDWiener=True`.
        WienerFiltTime (int): Wiener window size along the time axis, in time steps.
            Used only with `doSVDWiener=True`.
        WienerFiltLagTime (int): Wiener window size along the lag axis, in samples.
            Used only with `doSVDWiener=True`.
        StackCount (int): Number of consecutive correlation records per stack, e.g. `10`.
            `1` does not apply stacking.
        StackOverlap (float): Overlap fraction between successive groups, between `0` and `1`.
            `0` gives disjoint groups; `0.5` gives half overlap.

    Example:
        Stack correlation functions over ten time steps, with no overlap between groups:

        ```python
        from sda.process import xcorr_noise_postprocessing

        xcorr_noise_postprocessing(
            outputPath="/path/to/output",
            starttime="2023-01-01",
            endtime="2023-02-01",
            NumberOfProcesses=4,
            StackCount=10,
            StackOverlap=0,
        )
        ```

        Apply an SVD-Wiener filter without any stacking:

        ```python
        xcorr_noise_postprocessing(
            outputPath="/path/to/output",
            starttime="2023-01-01",
            endtime="2023-04-01",
            NumberOfProcesses=4,
            doSVDWiener=True,
            SVDThreshold=5,
            WienerFiltTime=5,
            WienerFiltLagTime=5,
        )
        ```
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
        "StackCount" : StackCount,
        "StackOverlap" : StackOverlap,
    }
    add_log("Configuration parameters:", level="info")
    for key in config:
        add_log(f"  - {key} : {config[key]}", level="info")
             
    pairs = MakeCouplesOfStation(config)
    add_log("Starting postprocessing of ambient noise correlations...", level="info")

    # Run in multiprocessing
    PostProcessingParallelWithConfig = partial(PostProcessingPair, config=config)
    with get_context("loky").Pool(processes=config["NumberOfProcesses"], initializer=init_worker_logging,
              initargs=get_worker_logging_config()) as p:
        with tqdm(total=len(pairs), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " PostProcessing  ")
            for _ in p.imap_unordered(PostProcessingParallelWithConfig, pairs):
                pbar.update()

    add_log("End process: xcorr_noise_postprocessing", level="info")
    add_log("#"*50, level="info")
