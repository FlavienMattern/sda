################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Main functionality: provide a processing of traces.

Module tracesMain
=================

Provide a function :func:`treatTracesFromDirectory` in order to make all
the treatment of the traces (see :doc:`tracesOverview`).

Before running this function, it is necessary to set the parameters in the module :mod:`traces.tracesParam`
and to define the treatment in the module :mod:`traces.tracesDefineTreatments`

Running the module:
-------------------

For whisper users, suppose you have the directory **traces** (the package), simply type:

.. code-block:: python

    $ cd traces
    $ python2.7 tracesMain.py

Python necessary libraries:
---------------------------

* python2.7
* scipy
* numpy
* obspy

More precisely we use at the present time:

.. code-block:: python

    >>> import numpy
    >>> numpy.__version__
    '1.5.0'
    >>> import scipy
    >>> scipy.__version__
    '0.9.0.dev6939'
    >>> import obspy.core
    >>> obspy.core.__version__
    '0.4.7'
    >>> import obspy.signal
    >>> obspy.signal.__version__
    '0.4.8'
    >>> import obspy.sac
    >>> obspy.sac.__version__
    '0.4.6'
    >>> import obspy.mseed
    >>> obspy.mseed.__version__
    '0.4.7'



"""
import sys
import os
import time
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesGetParam
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesExceptions
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesGeneratorPath
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesWriter
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesTreatment
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesDictOfTraces
from datetime import datetime, timedelta
from obspy import read_inventory



def treatTracesFromDirectory(config):
    """
    See the general specification.
    """
    try:
        parameters = tracesGetParam.Param(config)
        treatment = tracesTreatment.TreatmentTrace(param=parameters)
        if parameters.FormatTraceSave == 'mat':
            writeTrace = tracesWriter.WriterOneTraceMat(parameters)
        elif parameters.FormatTraceSave == 'npy':
            writeTrace = tracesWriter.WriterOneTraceNpy(parameters)
    except tracesExceptions.ExceptionTraces as msg:
        # print(msg)
        raise
    
    if os.path.isdir(parameters.SaveDirectory):
        sys.stdout.flush()
    
    generatorTrace = tracesGeneratorPath.generatorArrayBeTreatFrequenceAndPathSave(param=parameters, writer=writeTrace, config=config)

    BeginTimeTotal = time.time()
    BeginTimeDate = time.time()
    NumberOfTracesOneDate = 0
    NumberOfTracesTotal = 0

    # acorr = config["AutoCorr"]
    acorr = True
    remove_response = config['remove_response']
    
    # Read inventory file
    if remove_response:
        for path, subdirs, files in os.walk(config['inventory_path']):
            for name in files:
                if name[-4:] == ".xml":
                    invfile = os.path.join(path, name)
                    inv = read_inventory(invfile, format="STATIONXML")
                    try:
                        inventory.extend(inv)
                    except NameError:
                        inventory = inv

    for date, Trace, Frequence, DirPathSave, FileSave, StationFullName in generatorTrace:
        #print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), end=" ")
        #print("[INFO]      │  {}".format(date))
        
        if len(Trace) == 0: continue
        
        try:
            day = datetime(int(date.split("/")[0]),1,1) + timedelta(days=int(date.split("/")[1])-1)

            if remove_response:
                response_dict = {
                    'start': day,
                    'station_name': StationFullName,
                    'inventory':inventory,
                    'water_level':config['water_level'],
                    'pre_filt':config['response_prefilt']
                    }
            else:
                response_dict = {}
            
            
            acorrDirPathSave = f"_TRACE_ACORR{os.sep}".join(DirPathSave.rsplit(f"_TRACE{os.sep}",1))
            
            
            # import matplotlib.pyplot as plt
            # import numpy as np
            
            # xmin, xmax = (0, 24)
            # plt.figure(figsize=(10,8))
            # plt.title(StationFullName, y=1.1)
            # plt.axis("off")
            # plt.subplot(211)
            # timeTR = np.linspace(0, 24, len(Trace))
            # plt.title("Raw trace")
            # plt.plot(timeTR, Trace, lw=0.5, color="black")
            # plt.ylim(-1e5, 1e5)
            # plt.xlim(xmin, xmax)
            TraceW, TraceNoW = treatment.makeTreatment(Trace, Frequence, acorr, remove_response, response_dict, config)
            
            # plt.subplot(212)
            # timeTR = np.linspace(0, 24, len(TraceW))
            # plt.title("Processed Trace")
            # plt.plot(timeTR, TraceW, lw=0.5, color="black")
            # plt.xlim(xmin, xmax)
            # plt.savefig("/data4/fmattern/alsace_subsample/logs/Trace.png")
            
            writeTrace.writeOneTrace(DirPathSave, FileSave, TraceW)
            writeTrace.writeOneTrace(acorrDirPathSave, FileSave, TraceNoW)
            
            NumberOfTracesOneDate += 1
            if date is not None:
                sys.stderr.flush()
                sys.stdout.flush()
                BeginTimeDate = time.time()
                NumberOfTracesTotal += NumberOfTracesOneDate
                NumberOfTracesOneDate = 0
        except Exception as Err:
            print(f"Error while preprocessing {StationFullName} for day {day} : \n{Err}")
        

if __name__ == '__main__':
    treatTracesFromDirectory(config)
