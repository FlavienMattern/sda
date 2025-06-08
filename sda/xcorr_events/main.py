import itertools as it
import numpy as np
import glob
import os
import pandas as pd
from obspy import read
import multiprocessing
from functools import partial
from tqdm import tqdm
from datetime import datetime
import time
import scipy
from obspy.signal.filter import bandpass

import concurrent.futures
import collections

from scipy.signal import correlate
import matplotlib.pyplot as plt



def Correlate(Trace1, Trace2, config):
    
    Nsamples = len(np.arange(-config["Maxlag"], config["Maxlag"], 1/config["NewFrequence"]))*2+1
    maxLag = int(config["Maxlag"]*config["NewFrequence"])
    trace01 = np.zeros(Nsamples)
    trace01[:len(Trace1.data)] = Trace1.data
    trace02 = np.zeros(Nsamples)
    trace02[:len(Trace2.data)] = Trace2.data
    LenTrace = len(trace01)
    GoodNumber = int(LenTrace + maxLag)
    
    tr2 = np.zeros(GoodNumber)
    tr2[0:LenTrace] = trace01
    tr2[0:LenTrace] /= np.sqrt(np.sum(tr2[0:LenTrace]**2))
    tr2 = scipy.fftpack.fft(tr2,overwrite_x=True)
    tr2.imag *= -1 # Take complex conjugate
    tr1 = np.zeros(GoodNumber)
    tr1[maxLag:maxLag+LenTrace]= trace02
    tr1[maxLag:maxLag+LenTrace] /= np.sqrt(np.sum(tr1[maxLag:maxLag+LenTrace]**2))
    tr2 *= scipy.fftpack.fft(tr1,overwrite_x=True) # Compute cross correlation by multiplying spectrum in frequency domain
    
    xcorr = scipy.fftpack.ifft(tr2,overwrite_x=True)[0:2*maxLag+1].real
    lags = np.linspace(-config["Maxlag"], +config["Maxlag"], len(xcorr))


    
    # if (Trace1.stats.station=="R45CC") and (Trace2.stats.station=="R4B4A"):
    #     import matplotlib.pyplot as plt
    #     plt.figure()
    #     t = np.linspace(0, len(trace01)/config["NewFrequence"], len(trace01))
    #     plt.subplot(211)
    #     plt.title("R45CC - R4B4A")
    #     plt.plot(t, trace01/np.max(trace01)-0.5, color="black", lw=0.5)
    #     plt.plot(t, trace02/np.max(trace02)+0.5, color="red", lw=0.5)
    #     plt.subplot(212)
    #     plt.plot(lags, xcorr, color="black", lw=0.5)
    #     plt.savefig("/media/flavien/WORK/sda/sda/run/xcorr_evens.png", dpi=300)
    #     plt.close()
    
    return lags, xcorr

def PreProcessingBeforeResampling(Trace, config):
    # You can add your own preprocessing before resampling here
    return Trace



def Resampling(Trace, config):
    
    Trace.resample(config["NewFrequence"])
    
    return Trace
    


def PreProcessingAfterResampling(Trace, config):
    
    Trace.data = bandpass(Trace.data, config["freqMin"], config["freqMax"], config["NewFrequence"], corners=4, zerophase=True)
    
    # Whitening
    TraceW = Trace.copy() # Whitening(Trace, config)
    TraceNoW = Trace.copy()
    
    return TraceW, TraceNoW



def Whitening(Trace, config):
    fs = Trace.stats.sampling_rate
    bandfilt = [config["freqMin"], config["freqMax"]]
    
    data = Trace
    fftdata = np.fft.fft(data-np.mean(data))
    f = np.fft.fftfreq(len(data), 1/fs)
    
    # where to apply boxcard whitening
    iw = np.where( (f<=bandfilt[1]    ) * (f>=bandfilt[0]    ))[0]  
    # where to sin taper fmin
    iwstart = np.where( (f<=bandfilt[0]+1) * (f>=bandfilt[0]    ))[0]  
    # where to cos taper fmax
    iwend = np.where( (f<=bandfilt[1]    ) * (f>=bandfilt[1]-1))[0]  

    # box card whitening
    dataw = fftdata*0
    dataw[iw] = fftdata[iw]/np.abs(fftdata[iw])
    
    # cos/sin tapering box limits
    tapersin = np.sin(np.pi/2*np.linspace(0,1,len(iwstart)))**2
    tapercos = np.cos(np.pi/2*np.linspace(0,1,len(iwend)))**2 
    dataw[iwstart] = dataw[iwstart]*tapersin
    dataw[iwend] = dataw[iwend]  *tapercos
    
    dataw = 2*np.real(np.fft.ifft(dataw))
    
    Trace.data = dataw
    
    return Trace



def CorrelationParallel(folder, config):
    
    # Liste des couples qui peuvent être corrélés
    # stationsFiles = glob.glob(os.path.join(config["outputPath"], "events_catalog", folder, "*"))
    # stations = [os.path.split(elt)[-1].split(".")[0].split("_")[0] for elt in stationsFiles]
    stations = config["stations"]
    date_str = datetime.strptime(os.path.split(folder)[-1], "%Y%m%d_%H%M%S.%f").strftime("%Y-%m-%dT%H:%M:%S.%f")

    # Preprocessing
    StreamCross = read().clear()
    StreamAuto = read().clear()
    for sta in stations:
        for comp in config["Components"]:
            filePath = os.path.join(folder, f"{sta}_{comp}.mseed")
            
            # Check if file exists
            if not os.path.exists(filePath): continue
            Trace = read(filePath)[0]
            
            # Compute preprocessing
            Trace = PreProcessingBeforeResampling(Trace, config)
            Trace = Resampling(Trace, config)
            TraceW, TraceNoW = PreProcessingAfterResampling(Trace, config)
            
            StreamCross += TraceW
            StreamAuto += TraceNoW

    
    # Correlations
    buffer = []
    pairs = list(it.combinations_with_replacement(stations, 2))
    for sta1, sta2 in pairs:
        for comp1, comp2 in config["CrossComponents"]:
            
            # Load Traces
            if sta1 != sta2:
                Stream1 = StreamCross.select(station=sta1, channel=f"*{comp1}")
                Stream2 = StreamCross.select(station=sta2, channel=f"*{comp2}")
            else:
                Stream1 = StreamAuto.select(station=sta1, channel=f"*{comp1}")
                Stream2 = Stream1.copy()
                
            if len(Stream1) == 0 or len(Stream2) == 0:
                continue
            else:
                Trace1 = Stream1[0]
                Trace2 = Stream2[0]
                
            # test on realignment
            # # Trace1plot = Trace1.data/np.max(np.abs(Trace1.data))
            # # Trace2plot = Trace2.data/np.max(np.abs(Trace2.data))
                
            # if sta1 != sta2:
            #     T = len(Trace1.data)*Trace1.stats.delta
            #     t = np.arange(0, T, Trace1.stats.delta)
                
            #     # plt.figure(figsize=(10,14))
            #     # plt.subplot(311)
            #     # plt.plot(t, Trace1plot-1, color="black", lw=1)
            #     # plt.plot(t, Trace2plot+1, color="red", lw=1)
            #     # plt.xlim(15, 30)
            #     # plt.axvline(21.8)
            #     # plt.axvline(22.4)
                    
            #     #######
            #     # Make realignment here if necessary
            #     xcorr = correlate(Trace1.data, Trace2.data, mode='full')
            #     # tcorr = np.linspace(-T, T, len(xcorr))
            #     lag = np.argmax(np.abs(xcorr))#  - (len(Trace1.data) - 1)
            #     lag = 1588
            #     # print(len(Trace1), lag)
            #     Trace1.data = np.roll(Trace1.data, -lag)
            #     #######
                
            #     Trace1plot = Trace1.data/np.max(np.abs(Trace1.data))
            #     Trace2plot = Trace2.data/np.max(np.abs(Trace2.data))
                
            #     # plt.subplot(312)
            #     # plt.plot(t, Trace1plot-1, color="black", lw=1)
            #     # plt.plot(t, Trace2plot+1, color="red", lw=1)
            #     # plt.axvline(t[lag], color="red", ls="--")
            #     # plt.xlim(15, 30)
                
            #     # plt.savefig("/data1/fmattern/WORK/sda/sda/run/test_realign.png", dpi=300)
                
            # Compute correlations
            _, corr = Correlate(Trace1, Trace2, config)
            # corr_df = pd.DataFrame({"LagTime":lag, "Correlation":corr})
            folder_save = os.path.join(config["outputPath"], "xcorr_events", f"{comp1}{comp2}")
            try:
                os.makedirs(folder_save)
            except:
                pass
            filename = os.path.join(folder_save, f"{sta1}-{sta2}.csv")
            line = date_str + "".join([f",{c}" for c in corr]) + "\n"
            buffer.append((filename, line))

    return buffer
            

def save_results(buffer, lags):
    for filename, lines in buffer.items():
        if not os.path.exists(filename):
            lines = "".join([f",{l}" for l in lags]+["\n"]+lines)
        with open(filename, "a") as f:
            f.writelines(lines)


def run(
    outputPath,
    NumberOfProcesses = 1,
    stations = [],
    CrossComponents = ["ZZ"],
    Components = ["Z"],
    freqMin = 0.5,
    freqMax = 5,
    NewFrequence = 20,
    Maxlag = 20,
    format_results = True
    ):
    
    if len(stations) == 0:
        stations = []
        for dirpath, _, filenames in os.walk(os.path.join(outputPath, "events_catalog")):
            for filename in filenames:
                if filename[-6:] == ".mseed":
                    st_name = filename.split("_")[0]
                    if st_name not in stations:
                        stations.append(st_name)
    
    config = {
        "outputPath": outputPath,
        "NumberOfProcesses": NumberOfProcesses,
        "CrossComponents": CrossComponents,
        "Components": Components,
        "freqMin": freqMin,
        "freqMax": freqMax,
        "NewFrequence": NewFrequence,
        "Maxlag": Maxlag,
        "format_results": format_results,
        "stations": stations
    }  
    
    # Liste des événements
    eventFolders = glob.glob(os.path.join(outputPath, "events_catalog", "*"))
    eventFolders.sort()
    # eventFolders = [eventFolders[513]]
    # print(eventFolders)
    lags = np.linspace(-Maxlag, +Maxlag, Maxlag*NewFrequence*2+1) 

    buffer = collections.defaultdict(list)
    total_lines = 0
    buffer_size = 10000
    with concurrent.futures.ProcessPoolExecutor(max_workers=config["NumberOfProcesses"]) as executor:
        futures = {}

        with tqdm(total=len(eventFolders), desc="Correlations", unit="evt") as pbar:
            
            for folder in eventFolders:
                future = executor.submit(CorrelationParallel, folder, config)
                futures[future] = folder

            for future in concurrent.futures.as_completed(futures):
                folder = futures[future]
                result = future.result()
                
                for filename, line in result:
                    buffer[filename].append(line)
                    total_lines += 1

                    if total_lines >= buffer_size:
                        save_results(buffer, lags)
                        buffer.clear()
                        total_lines = 0
                        
                pbar.update(1)

            # Final flush: vider tout le contenu restant dans les buffers
            if buffer:
                save_results(buffer, lags)
                buffer.clear()
                
    
    ### Formatting data            
    if config["format_results"]:
        
        corr_path = "/data4/fmattern/xcorr_events/xcorr_events"
    
        todo_files = []
        for dirpath, _, filenames in os.walk(corr_path):
            for filename in filenames:
                if filename[-4:] == ".csv":
                    todo_files.append(os.path.join(dirpath, filename))
        
        def reader(file_list, queue):
            for file_path in file_list:
                df = pd.read_csv(file_path, index_col=0)
                queue.put((file_path, df)) 
            queue.put(None) # End marker of the queue

        def writer(queue, progress, lock):
            while True:
                item = queue.get()
                if item is None:
                    queue.put(None) # End marker of the queue
                    break

                file_path, df = item
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                df.to_csv(file_path)

                with lock: # Protecting concurrent access
                    progress.value += 1

        def progress_bar(total, progress):
            with tqdm(total=total, desc="Formatting results", position=0, leave=True) as pbar:
                while progress.value < total:
                    pbar.n = progress.value
                    pbar.refresh()
                pbar.n = total
                pbar.refresh()
                
        manager = multiprocessing.Manager()
        queue = multiprocessing.Queue()
        progress = manager.Value("i", 0)
        lock = manager.Lock()

        reader_proc = multiprocessing.Process(target=reader, args=(todo_files, queue))
        writer_procs = [
            multiprocessing.Process(target=writer, args=(queue, progress, lock))
            for _ in range(config["NumberOfProcesses"])
        ]
        progress_proc = multiprocessing.Process(target=progress_bar, args=(len(todo_files), progress))

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


    
    
    