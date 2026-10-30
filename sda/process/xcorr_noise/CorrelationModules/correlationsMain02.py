################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################

import sys
import os

from sda.process.xcorr_noise.CorrelationModules import correlationsExceptions, correlationsGetParam, correlationsCorrelation, correlationsGeneratorPath, correlationsWriter, correlationsLoader
from sda.core.date_utils import get_day
from sda.core.stations_define import ReadListOfStation
import sda.process.xcorr_noise.PreProcessingModules.tracesPreProcessing as PreProcessing
from sda.core.logs import add_log
import traceback
import h5py
import time
import shutil
from datetime import datetime
from multiprocessing import Pool, Lock
from functools import partial
from tqdm import tqdm
import numpy as np
from obspy import read_inventory, UTCDateTime
import geopy.distance


def save_xcorr(save_directory, sta1, sta2, day, comp, corr, max_lag, fs,
               config, n_retained, indices, data_coverage):
        global lock
        foldername = os.path.join(save_directory, comp)
        filename = os.path.join(foldername, f"{sta1}-{sta2}.h5")
        os.makedirs(foldername, exist_ok=True)

        try:
            with lock:
                with h5py.File(filename, 'a') as f:
                    if "metadata" not in f:
                        meta_grp = f.create_group("metadata")
                        meta_grp.create_dataset('fs', data=fs)
                        meta_grp.create_dataset('max_lag', data=max_lag)
                    meta_grp = f["metadata"]
                    if "correlations" not in f:
                        f.create_group("correlations")
                    if day in f["correlations"]:
                        del f["correlations"][day]
                    if corr is not None and corr.size:
                        f["correlations"].create_dataset(day, data=corr, compression="gzip", dtype="float32")

                    windows = meta_grp.require_group("windows")
                    if day in windows:
                        del windows[day]
                    record = windows.create_group(day)
                    record.attrs.update(start_ns=config["window_start_ns"], end_ns=config["window_end_ns"],
                                        n_retained=n_retained, n_total=config["numberOfSubTrace"],
                                        save_mode=config["save_mode"])
                    retained = np.zeros(config["numberOfSubTrace"], dtype=bool)
                    retained[indices] = True
                    record.create_dataset("retained", data=retained)
                    record.create_dataset("data_coverage", data=data_coverage)
        except:
            msg = f"Cannot save correlation {sta1}-{sta2} ({comp}) for interval {day}.\n"
            msg += traceback.format_exc()
            add_log(msg, level="error")


def makeCorrFromDirectoryTraces(config):

    try:
        parameters = correlationsGetParam.Param(config)
        parameters.ListOfDates = [config["window_key"]]
        correlation = correlationsCorrelation.CorrelationForSublen(config)
        writeCorr = correlationsWriter.WriterCorrelation(parameters)

        loadTrace = correlationsLoader.LoaderOneTraceNpy(parameters, acorr=False)
    
    except correlationsExceptions.ExceptionCorrelations as msg:
        # print(msg)
        raise
    
    generatorCouple = correlationsGeneratorPath.GeneratorDateCoupleNotSaveOneListStation(param=parameters, writer=writeCorr)
        
    if config['maxInterDistance'] != None:
        for path, subdirs, files in os.walk(config['inventory_path']):
            for name in files:
                if name[-4:] == ".xml":
                    invfile = os.path.join(path, name)
                    inv = read_inventory(invfile, format="STATIONXML")
                    try:
                        inventory.extend(inv)
                    except NameError:
                        inventory = inv

    fs = config["NewFrequence"]
    max_lag = config["Maxlag"] / fs

    for DirSave, FileSave, date, sta1, sta2 in generatorCouple:

        DirSave_split = DirSave.split(os.sep)
        date_str = os.path.basename(FileSave).split(".")[0]
        comp = DirSave_split[-2]
        save_directory = config['SaveDirectory']
        
        if config['maxInterDistance'] != None:
            lat1 = inventory.select(station=sta1)[0][0].latitude
            lon1 = inventory.select(station=sta1)[0][0].longitude
            lat2 = inventory.select(station=sta2)[0][0].latitude
            lon2 = inventory.select(station=sta2)[0][0].longitude
            dist = geopy.distance.geodesic((lat1,lon1), (lat2,lon2)).km

            # Skip if distance inter station is too high
            if dist > config['maxInterDistance']:
                continue

        traces = []
        coverage = []
        for component, station in zip(comp, (sta1, sta2)):
            directory, filename = loadTrace.getDirAndFileLoadTrace(component, date, station, sta1 == sta2)
            try:
                traces.append(loadTrace.loadOneTrace(directory, filename))
            except Exception:
                traces.append(None)
            coverage_file = os.path.join(config['SaveDirectory'], component + "_TRACE", date, station + ".npy.coverage.npy")
            try:
                coverage.append(np.load(coverage_file))
            except Exception:
                coverage.append(np.full(config['numberOfSubTrace'], np.nan))

        n_retained = 0
        indices = np.array([], dtype=int)
        corr = None
        if all(trace is not None for trace in traces):
            corr, perc, n_retained, subcorrelations, indices = correlation.makeCorrelationSubLenStackWithNormalisationAndMaxlag(
                traces[0], traces[1], date_str, comp, sta1, sta2, return_details=True)
            if config['save_mode'] == 'subcorrelations':
                corr = subcorrelations
            elif not n_retained or perc < config['minSubCorrKeep']:
                corr = None
        save_xcorr(save_directory, sta1, sta2, date_str, comp, corr, max_lag, fs,
                   config, n_retained, indices, np.column_stack(coverage))


def CorrelationParallel(interval, config):
    
    xcorr_path = config['SaveDirectory']
    
    config = dict(config)
    start_ns, end_ns = interval
    start = UTCDateTime(ns=start_ns, precision=9)
    end = UTCDateTime(ns=end_ns, precision=9)
    first = UTCDateTime(ns=(start_ns // 1_000_000_000) * 1_000_000_000)
    last = UTCDateTime(ns=((end_ns - 1) // 1_000_000_000) * 1_000_000_000)
    config["starttimeAll"] = config["starttime"]
    config["endtimeAll"] = config["endtime"]
    config["starttime"] = str(start)
    config["endtime"] = str(end)
    config["window_start_ns"] = start_ns
    config["window_end_ns"] = end_ns
    config["FirstYear"], config["FirstDay"] = first.year, first.julday
    config["LastYear"], config["LastDay"] = last.year, last.julday
    config["stations"] = ReadListOfStation(config)
    if config["window_duration_ns"] == 86400 * 1_000_000_000 and start_ns % (86400 * 1_000_000_000) == 0:
        config["window_key"] = first.strftime("%Y/%j")
    else:
        config["window_key"] = os.path.join("windows", f"{start_ns}_{end_ns}")

    # Run PreProcessing step for each component
    add_log(f"Preprocessing interval [{start}, {end})")
    for ComponentStation in config["Components"]:
        config["ComponentStation"] = ComponentStation
        PreProcessing.treatTracesFromDirectory(config)

    # Computing cross correlations
    config["TypeListStations"] = "oneList"
    config["NumberSubListOfDates"] = "1"
    config["IndexSublistDates"] = "0"
    config["NumberSubListOfStations"] = "1"
    config["IndexSublistStations"] = "0"
    add_log(f"Correlating interval [{start}, {end})")
    for comp in config['CrossComponents']:
        comp1 = comp[0]
        comp2 = comp[1]
        config["ComponentFirstStation"] = comp1
        config["ComponentSecondStation"] = comp2
        try:
            makeCorrFromDirectoryTraces(config)
        except:
            msg = f"An error occurred while correlating interval [{start}, {end}) and {comp} components. Skipping interval.\n"
            msg += traceback.format_exc()
            add_log(msg, level="error")
            continue
    add_log(f"End Correlating interval [{start}, {end})")
    
    # Removing preprocessed files
    if not config["savePreProcessing"]:
        for c in config["Components"]:
            foldername = os.path.join(xcorr_path, f"{c}_TRACE", config["window_key"])
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
            foldername = os.path.join(xcorr_path, f"{c}_TRACE_ACORR", config["window_key"])
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)


def init_worker(l):
    global lock
    lock = l


def Correlation(config):

    xcorr_path = config['SaveDirectory']
    starttime = config["range_start_ns"]
    endtime = config["range_end_ns"]
    duration = config["window_duration_ns"]
    number_intervals, remainder = divmod(endtime - starttime, duration)
    add_log(f"Starting correlation computation between {UTCDateTime(ns=starttime)} and {UTCDateTime(ns=endtime)}...", level="info")
    if remainder:
        add_log(f"Skipping incomplete final interval ({remainder / 1e9:g} seconds).", level="warning")
    intervals = ((starttime + i * duration, starttime + (i + 1) * duration) for i in range(number_intervals))

    # Run in multiprocessing
    lock = Lock() # to prevent simultaneous access to saved files
    CorrelationParallelWithConfig = partial(CorrelationParallel, config=config)
    with Pool(processes=config["NumberOfProcesses"], initializer=init_worker, initargs=(lock,)) as p:
        with tqdm(total=number_intervals, bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Correlations    ")
            for _ in p.imap_unordered(CorrelationParallelWithConfig, intervals):
                pbar.update()

    # Removing folders
    if not config["savePreProcessing"]:
        for c in config["Components"]:
            foldername = os.path.join(xcorr_path, f"{c}_TRACE")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
                add_log(f"Remove preprocessed traces folder: {foldername}", level="info")
            foldername = os.path.join(xcorr_path, f"{c}_TRACE_ACORR")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
                add_log(f"Remove preprocessed traces folder: {foldername}", level="info")
