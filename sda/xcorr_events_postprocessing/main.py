import os
import pandas as pd
from datetime import datetime
import numpy as np
import scipy.signal
from tqdm import tqdm
import multiprocessing


def SVDWiener(data, config):
    threshold = config["SVDThreshold"]
    K = config["WienerFiltTime"] # Wiener window in date dimension (smoothing of K days)
    L = config["WienerFiltLagTime"] # Wiener window in lag time dimension (1/L * fs = lag time smoothing)
    C = data

    idxGood = ~np.all(np.isnan(C), axis=0)
    C = C[:,idxGood]
    
    for i in range(2):
        # Apply SVD
        U, Sval, Vt = np.linalg.svd(C, full_matrices=True)
        S = np.zeros(np.shape(C))
        S[:threshold, :threshold] = np.diag(Sval[:threshold])
        CSVD = U.dot(S).dot(Vt)

        # Apply Wiener
        CSVDWiener = scipy.signal.wiener(CSVD, (L, K))
        
        C = CSVDWiener
    
    dataFilt = np.zeros( (data.shape[0], data.shape[1]) ) * np.nan
    dataFilt[:,idxGood] = C
    
    return dataFilt


def reader(file_list, queue, config):
    for file_path in file_list:
        df = pd.read_csv(file_path, index_col=0)
        if config["doSVWiener"] and ( (len(df.index) < config["SVDThreshold"]) or (len(df.index) < config["WienerFiltTime"]) ):
            queue.put("empty")
            continue
        comp, filename = os.path.split(file_path)
        comp = comp[-2:]
        save_file = os.path.join(config["results_path"], comp, filename)
        queue.put((save_file, df))
    queue.put(None) # End marker of the queue


def process(queue, progress, lock, config):
    while True:
        item = queue.get()
        if item is None:
            queue.put(None) # End marker of the queue
            break
        if item == "empty":
            with lock: # Protecting concurrent access
                progress.value += 1
            continue
        
        save_path, df = item
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.columns = df.columns.astype(float)
        data =  df.values.T
        
        ####################################################################
        # Post processiing of correlation matrix
        data = data / np.sum(data**2, axis=0)
        try:
            if config["doSVWiener"]:data = SVDWiener(data, config)
        except Exception as err:
            print(f"Error while computing SVD-Wiener filter for {save_path}. Skipping...\n{err}")
            with lock: # Protecting concurrent access
                progress.value += 1
            continue
        ####################################################################
            
        # Update dataframe and save it
        df.loc[:, :] = data.T
        save_folder = os.path.split(save_path)[0]
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)
        df.to_csv(save_path)

        with lock: # Protecting concurrent access
            progress.value += 1


def progress_bar(total, progress):
    with tqdm(total=total, desc="PostProcessing", position=0, leave=True) as pbar:
        while progress.value < total:
            pbar.n = progress.value
            pbar.refresh()
        pbar.n = total
        pbar.refresh()


def run(
    outputPath,
    NumberOfProcesses,
    doSVWiener = True,
    SVDThreshold = 15,
    WienerFiltTime = 5,
    WienerFiltLagTime = 5
):
    corr_path = os.path.join(outputPath, "xcorr_events")
    results_path = os.path.join(outputPath, "xcorr_events_postprocessing")
    
    config = {
        "outputPath": outputPath,
        "corr_path": corr_path,
        "results_path": results_path,
        "NumberOfProcesses": NumberOfProcesses,
        "doSVWiener": doSVWiener,
        "SVDThreshold": SVDThreshold,
        "WienerFiltTime": WienerFiltTime,
        "WienerFiltLagTime": WienerFiltLagTime,
    }
    
    files = []
    for dirpath, _, filenames in os.walk(corr_path):
        for filename in filenames:
            if filename[-4:] == ".csv":
                files.append(os.path.join(dirpath, filename))
    
    ##################################
    # files = files[:10]
    manager = multiprocessing.Manager()
    queue = multiprocessing.Queue()
    progress = manager.Value("i", 0)
    lock = manager.Lock()

    reader_proc = multiprocessing.Process(target=reader, args=(files, queue, config))
    writer_procs = [
        multiprocessing.Process(target=process, args=(queue, progress, lock, config))
        for _ in range(config["NumberOfProcesses"])
    ]
    progress_proc = multiprocessing.Process(target=progress_bar, args=(len(files), progress))

    # Starting processes
    reader_proc.start()
    for p in writer_procs:
        p.start()
    progress_proc.start()

    # Waiting for all processes to stop
    reader_proc.join()
    for p in writer_procs:
        p.join()
    progress_proc.join()
            
            
    
    
    
    
    
    
    
    