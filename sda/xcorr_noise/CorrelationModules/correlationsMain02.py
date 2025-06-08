################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
import sys
import os
cwd = os.getcwd()
file_pwd = "/".join(__file__.split("/")[:-1])
sys.path.append(cwd)
sys.path.append(file_pwd)


# import correlationsGetParam
# import correlationsExceptions
# import correlationsCorrelation
# import correlationsGeneratorPath
# import correlationsWriter
# import correlationsLoader

from sda.xcorr_noise.CorrelationModules import correlationsGetParam
from sda.xcorr_noise.CorrelationModules import correlationsExceptions
from sda.xcorr_noise.CorrelationModules import correlationsCorrelation
from sda.xcorr_noise.CorrelationModules import correlationsGeneratorPath
from sda.xcorr_noise.CorrelationModules import correlationsWriter
from sda.xcorr_noise.CorrelationModules import correlationsLoader

from sda.functions.date_utils import get_day
import sda.xcorr_noise.PreProcessingModules.tracesPreProcessing as PreProcessing
from sda.functions.stations_define import ReadListOfStation, MakeCouplesOfStation

import time
import shutil
from datetime import datetime, timedelta
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm
import numpy as np
import pickle as pkl
from obspy import read_inventory
import geopy.distance




def makeCorrFromDirectoryTraces(config):

    try:
        parameters = correlationsGetParam.ParamWithLastDateCompute(config)
        correlation = correlationsCorrelation.CorrelationForSublen(config)
        
        if parameters.FormatSave == 'mat':
            writeCorr = correlationsWriter.WriterOneCorrelationMat(parameters)
        elif parameters.FormatSave == 'npy':
            writeCorr = correlationsWriter.WriterOneCorrelationNpy(parameters)

        if parameters.FormatTrace == 'mat':
            loadTrace = correlationsLoader.LoaderOneTraceMat(parameters, acorr=False)
        elif parameters.FormatTrace == 'npy':
            loadTrace = correlationsLoader.LoaderOneTraceNpy(parameters, acorr=False)
    
    except correlationsExceptions.ExceptionCorrelations as msg:
        # print(msg)
        raise
    
    if parameters.TypeListStations == 'oneList':
        generatorCouple = correlationsGeneratorPath.GeneratorPathSaveOneDateCoupleArraysOneList(param=parameters, loader=loadTrace, writer=writeCorr)
    elif parameters.TypeListStations == 'twoLists':
        generatorCouple = correlationsGeneratorPath.GeneratorPathSaveOneDateCoupleArraysTwoLists(param=parameters, loader=loadTrace, writer=writeCorr)
    else:
        sys.exit()
        
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

    for DirSave, FileSave, date, firstTrace, secondTrace in generatorCouple:

        DirSave = os.path.normpath(DirSave)
        DirSave_split = DirSave.split(os.sep)
        date_str = DirSave_split[-3] + "/" + DirSave_split[-2]
        date_str = datetime.strptime(date_str, '%Y/%j')
        date_str = date_str.strftime('%Y-%m-%d')
        comp = DirSave_split[-4].split("_")[0]
        sta1 = FileSave.split(".")[0].split("_")[0]
        sta2 = FileSave.split(".")[0].split("_")[-1]
        
        if config['maxInterDistance'] != None:
            lat1 = inventory.select(station=sta1)[0][0].latitude
            lon1 = inventory.select(station=sta1)[0][0].longitude
            lat2 = inventory.select(station=sta2)[0][0].latitude
            lon2 = inventory.select(station=sta2)[0][0].longitude
            dist = geopy.distance.geodesic((lat1,lon1), (lat2,lon2)).km

            # Skip if distance inter station is too high
            if dist > config['maxInterDistance']:
                continue
        
        saveCorr = os.path.join(config["SaveDirectory"][:-4], "Correlations", "Raw", comp)
        filename = f"{sta1}-{sta2}.pkl"

        corr, perc = correlation.makeCorrelationSubLenStackWithNormalisationAndMaxlag(firstTrace, secondTrace, date_str, comp, sta1, sta2)
        
        # Keep Correlation if at least perc % of subcorr retained
        if perc >=config['minSubCorrKeep']:
            writeCorr.writeOneCorrelation(DirSave, FileSave, corr)
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
    for ComponentStation in config["Components"]:
        config["ComponentStation"] = ComponentStation
        PreProcessing.treatTracesFromDirectory(config)

    # Computing cross correlations
    config["TypeListStations"] = "oneList"
    config["NumberSubListOfDates"] = "1"
    config["IndexSublistDates"] = "0"
    config["NumberSubListOfStations"] = "1"
    config["IndexSublistStations"] = "0"
    for comp in config['CrossComponents']:
        comp1 = comp[0]
        comp2 = comp[1]
        config["ComponentFirstStation"] = comp1
        config["ComponentSecondStation"] = comp2
        try:
            makeCorrFromDirectoryTraces(config)
        except:
            print(f"error during corr {day}, skipping...")
            continue
    
    # Removing preprocessed files
    if not config["savePreProcessing"]:
        for c in ["Z","N","E"]:
            foldername = os.path.join(xcorr_path, f"{c}_TRACE", f"{FirstYear}", f"{FirstDay:03d}")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
            foldername = os.path.join(xcorr_path, f"{c}_TRACE_ACORR", f"{FirstYear}", f"{FirstDay:03d}")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)



def CorrelationPoolHandler(days, config):
    # We set config dict as a non iterable argument for parallel processing
    CorrelationParallelWithConfig = partial(CorrelationParallel, config=config)
    # Create Pool with a progress bar
    with Pool(processes=config["NumberOfProcesses"]) as p:
        with tqdm(total=len(days), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Correlations    ")
            for _ in p.imap_unordered(CorrelationParallelWithConfig, days):
                pbar.update()



def Correlation(config):
    xcorr_path = config['SaveDirectory']

    starttime = datetime.strptime(config["starttime"], "%Y-%m-%d")
    endtime = datetime.strptime(config["endtime"], "%Y-%m-%d")
    days = np.array([starttime + timedelta(days=i) for i in range( (endtime-starttime).days+1 )])
    
    # Remove old correlation folders
    # overwriteCorr = True
    # if overwriteCorr:
    #     try:
    #         shutil.rmtree(os.path.join(xcorr_path[:-4], "Correlations"))
    #     except:
    #         pass

    # Lancement du multiprocessing
    CorrelationPoolHandler(days, config)

    # Removing folders
    if not config["savePreProcessing"]:
        for c in ["Z","N","E"]:
            foldername = os.path.join(xcorr_path, f"{c}_TRACE")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
            foldername = os.path.join(xcorr_path, f"{c}_TRACE_ACORR")
            if os.path.isdir(foldername):
                shutil.rmtree(foldername)
