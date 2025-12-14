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
from datetime import datetime, timedelta
from multiprocessing import Pool, Lock
from functools import partial
from tqdm import tqdm
import numpy as np
from obspy import read_inventory
import geopy.distance



def save_xcorr( save_directory, sta1, sta2, day, comp, corr, max_lag, fs):
        
        global lock
        foldername = os.path.join(save_directory, f"{comp}")
        filename = os.path.join(foldername, f"{sta1}-{sta2}.h5")
        os.makedirs(foldername, exist_ok=True)

        try:
            with lock:  # To prevent simultaneous access to the file
                with h5py.File(filename, 'a') as f:

                    if "metadata" not in f:
                        meta_grp = f.create_group("metadata")
                        meta_grp.create_dataset('fs', data=fs)
                        meta_grp.create_dataset('max_lag', data=max_lag)

                    if "correlations" not in f:
                        f.create_group("correlations")

                    if day in f["correlations"]:
                        del f["correlations"][day]

                    corr_grp = f["correlations"]
                    corr_grp.create_dataset(
                        day,
                        data=corr,
                        compression="gzip",
                        dtype="float32"
                    )
        except:
            msg = f"Cannot save correlation {sta1}-{sta2} ({comp}) for day {day}.\n"
            msg += traceback.format_exc()
            add_log(msg, level="error")


def makeCorrFromDirectoryTraces(config):

    try:
        parameters = correlationsGetParam.ParamWithLastDateCompute(config)
        correlation = correlationsCorrelation.CorrelationForSublen(config)
        writeCorr = correlationsWriter.WriterOneCorrelation(parameters)

        if parameters.FormatTrace == 'mat':
            loadTrace = correlationsLoader.LoaderOneTraceMat(parameters, acorr=False)
        elif parameters.FormatTrace == 'npy':
            loadTrace = correlationsLoader.LoaderOneTraceNpy(parameters, acorr=False)
    
    except correlationsExceptions.ExceptionCorrelations as msg:
        # print(msg)
        raise
    
    generatorCouple = correlationsGeneratorPath.GeneratorPathSaveOneDateCoupleArraysOneList(param=parameters, loader=loadTrace, writer=writeCorr)
        
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

    NumberOfCorrOneDate = 0
    NumberOfCorrTotal = 0

    fs = config["NewFrequence"]
    max_lag = int(config["Maxlag"] / fs)

    for DirSave, FileSave, date, firstTrace, secondTrace in generatorCouple:

        DirSave_split = DirSave.split(os.sep)
        DirSave_split = DirSave.split(os.sep)
        date_str = os.path.basename(FileSave).split(".")[0]
        sta1, sta2 = DirSave_split[-1].split("-")
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

        corr, perc = correlation.makeCorrelationSubLenStackWithNormalisationAndMaxlag(firstTrace, secondTrace, date_str, comp, sta1, sta2)
        
        # Keep Correlation if at least perc % of subcorr retained
        if perc >=config['minSubCorrKeep']:
            save_xcorr(save_directory, sta1, sta2, date_str, comp, corr, max_lag, fs)
        NumberOfCorrOneDate += 1

        if date is not None:
            sys.stderr.flush()
            sys.stdout.flush()
            parameters.writeLastDateCompute(date)
            BeginTimeDate = time.time()
            NumberOfCorrTotal += NumberOfCorrOneDate
            NumberOfCorrOneDate = 0


def CorrelationParallel(day, config):
    
    xcorr_path = config['SaveDirectory']
    
    config["starttimeAll"] = config["starttime"]
    config["endtimeAll"] = config["endtime"]
    config["starttime"] = day.strftime("%Y-%m-%d")
    config["endtime"] = (day + timedelta(days=1)).strftime("%Y-%m-%d")
    FirstYear, FirstDay = get_day(config["starttime"])
    LastYear, LastDay = get_day(config["starttime"])
    config["FirstYear"] = FirstYear
    config["FirstDay"] = FirstDay
    config["LastYear"] = LastYear
    config["LastDay"] = LastDay
    config["stations"] = ReadListOfStation(config)

    # Run PreProcessing step for each component
    add_log(f"Preprocessing day {day.strftime('%Y-%m-%d')}")
    for ComponentStation in config["Components"]:
        config["ComponentStation"] = ComponentStation
        PreProcessing.treatTracesFromDirectory(config)

    # Computing cross correlations
    config["TypeListStations"] = "oneList"
    config["NumberSubListOfDates"] = "1"
    config["IndexSublistDates"] = "0"
    config["NumberSubListOfStations"] = "1"
    config["IndexSublistStations"] = "0"
    add_log(f"Correlating day {day.strftime('%Y-%m-%d')}")
    for comp in config['CrossComponents']:
        comp1 = comp[0]
        comp2 = comp[1]
        config["ComponentFirstStation"] = comp1
        config["ComponentSecondStation"] = comp2
        try:
            makeCorrFromDirectoryTraces(config)
        except:
            msg = f"An error occurred while correlating data for day {day} and {comp} components. Skipping day.\n"
            msg += traceback.format_exc()
            add_log(msg, level="error")
            continue
    add_log(f"End Correlating day {day.strftime('%Y-%m-%d')}")
    
    # Removing preprocessed files
    if not config["savePreProcessing"]:
        for c in ["Z","N","E"]:
            foldername = os.path.join(xcorr_path, f"{c}_TRACE", f"{FirstYear}", f"{FirstDay:03d}")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
            foldername = os.path.join(xcorr_path, f"{c}_TRACE_ACORR", f"{FirstYear}", f"{FirstDay:03d}")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)



def init_worker(l):
    global lock
    lock = l



def Correlation(config):

    xcorr_path = config['SaveDirectory']
    starttime = datetime.strptime(config["starttime"], "%Y-%m-%d")
    endtime = datetime.strptime(config["endtime"], "%Y-%m-%d")
    add_log(f"Starting correlation computation between {starttime} and {endtime}...", level="info")
    days = np.array([starttime + timedelta(days=i) for i in range( (endtime-starttime).days+1 )])

    # Run in multiprocessing
    lock = Lock() # to prevent simultaneous access to saved files
    CorrelationParallelWithConfig = partial(CorrelationParallel, config=config)
    with Pool(processes=config["NumberOfProcesses"], initializer=init_worker, initargs=(lock,)) as p:
        with tqdm(total=len(days), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Correlations    ")
            for _ in p.imap_unordered(CorrelationParallelWithConfig, days):
                pbar.update()

    # Removing folders
    if not config["savePreProcessing"]:
        for c in ["Z","N","E"]:
            foldername = os.path.join(xcorr_path, f"{c}_TRACE")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
                add_log(f"Remove preprocessed traces folder: {foldername}", level="info")
            foldername = os.path.join(xcorr_path, f"{c}_TRACE_ACORR")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
                add_log(f"Remove preprocessed traces folder: {foldername}", level="info")
