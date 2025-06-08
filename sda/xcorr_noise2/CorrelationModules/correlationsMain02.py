################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
import sys
import os
from sda.xcorr_noise2.CorrelationModules import correlationsGetParam
from sda.xcorr_noise2.CorrelationModules import correlationsExceptions
from sda.xcorr_noise2.CorrelationModules import correlationsCorrelation
from sda.xcorr_noise2.CorrelationModules import correlationsGeneratorPath
from sda.xcorr_noise2.CorrelationModules import correlationsWriter
from sda.xcorr_noise2.CorrelationModules import correlationsLoader

from sda.functions.date_utils import get_day
import sda.xcorr_noise2.PreProcessingModules.tracesPreProcessing as PreProcessing
from sda.functions.stations_define import ReadListOfStation

import time
import shutil
from datetime import datetime, timedelta

from functools import partial
from tqdm import tqdm
import numpy as np
import pickle as pkl
from obspy import read_inventory
import geopy.distance

# from multiprocessing import Pool
import concurrent.futures
import collections




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
    
    buffer = []

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
            # writeCorr.writeOneCorrelation(DirSave, FileSave, corr)
            folder_save = os.path.join(os.path.split(config["SaveDirectory"])[0], f"{comp}")
            try:
                os.makedirs(folder_save)
            except:
                pass
            filename = os.path.join(folder_save, f"{sta1}-{sta2}.csv")
            date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime('%Y-%m-%d %H:%M:%S')
            line = date_str + "".join([f",{c}" for c in corr]) + "\n"
            buffer.append((filename, line))
        NumberOfCorrOneDate += 1

        if date is not None:
            sys.stderr.flush()
            sys.stdout.flush()
            parameters.writeLastDateCompute(date)
            BeginTimeDate = time.time()
            NumberOfCorrTotal += NumberOfCorrOneDate
            NumberOfCorrOneDate = 0
            
    return buffer


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
    buffer = []
    for comp in config['CrossComponents']:
        comp1 = comp[0]
        comp2 = comp[1]
        config["ComponentFirstStation"] = comp1
        config["ComponentSecondStation"] = comp2
        try:
            sub_buffer = makeCorrFromDirectoryTraces(config)
            [buffer.append(s) for s in sub_buffer]
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
                
    return buffer



def save_results(buffer, lags):
    for filename, lines in buffer.items():
        if not os.path.exists(filename):
            lines = "".join([f",{l}" for l in lags]+["\n"]+lines)
        with open(filename, "a") as f:
            f.writelines(lines)
            
            

def CorrelationPoolHandler(days, config):
    
    NewFrequence = config["NewFrequence"]
    Maxlag = config["Maxlag"] / NewFrequence
    lags = np.linspace(-Maxlag, +Maxlag, int(Maxlag*NewFrequence*2+1)) 
    buffer = collections.defaultdict(list)
    total_lines = 0
    buffer_size = 500
               
    with concurrent.futures.ProcessPoolExecutor(max_workers=config["NumberOfProcesses"]) as executor:
        futures = {}

        with tqdm(total=len(days), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Correlations    ")
            
            for day in days:
                future = executor.submit(CorrelationParallel, day, config)
                futures[future] = day

            for future in concurrent.futures.as_completed(futures):
                day = futures[future]
                result = future.result()
                for filename, line in result:
                    buffer[filename].append(line)
                    total_lines += 1

                    # Flush buffer
                    if total_lines >= buffer_size:
                        save_results(buffer, lags)
                        buffer.clear()
                        total_lines = 0
                        
                pbar.update(1)

            # Final flush
            if buffer:
                save_results(buffer, lags)
                buffer.clear()



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
