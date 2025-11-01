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
import sys, os, time
from sda.process.xcorr_noise.PreProcessingModules.TraceModules import tracesGetParam, tracesExceptions, tracesGeneratorPath, tracesWriter, tracesTreatment
from sda.core.logs import add_log
from datetime import datetime, timedelta
from obspy import read_inventory
import traceback



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
       
        if len(Trace) == 0:
            add_log(f"Trace for station {StationFullName} and day {date} is empty. Skipping trace.", level="warning")
            continue
        
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
                response_dict = {
                    'start': day,
                    'station_name': StationFullName
                    }
            
            
            acorrDirPathSave = f"_TRACE_ACORR{os.sep}".join(DirPathSave.rsplit(f"_TRACE{os.sep}",1))
            
            #############################
            # import pickle as pkl
            # foldername = os.path.join("/media/flavien/WORK/these/schema/RESULTS/workflow_data", StationFullName.split(".")[1], day.strftime("%Y-%m-%d"))
            # try: 
            #     os.makedirs(foldername)
            # except:
            #     pass
            # filename = os.path.join(foldername, f"rawdata.pkl")
            # print(filename)
            # with open(filename, "wb") as f:
            #     pkl.dump(Trace, f)
            #############################

            TraceW, TraceNoW = treatment.makeTreatment(Trace, Frequence, acorr, remove_response, response_dict, config)
            
            #############################
            # import pickle as pkl
            # foldername = os.path.join("/media/flavien/WORK/these/schema/RESULTS/workflow_data", StationFullName.split(".")[1], day.strftime("%Y-%m-%d"))
            # filename = os.path.join(foldername, f"procdata.pkl")
            # print(filename)
            # with open(filename, "wb") as f:
            #     pkl.dump(TraceW, f)
            #############################
            
            writeTrace.writeOneTrace(DirPathSave, FileSave, TraceW)
            writeTrace.writeOneTrace(acorrDirPathSave, FileSave, TraceNoW)
            
            NumberOfTracesOneDate += 1
            if date is not None:
                sys.stderr.flush()
                sys.stdout.flush()
                BeginTimeDate = time.time()
                NumberOfTracesTotal += NumberOfTracesOneDate
                NumberOfTracesOneDate = 0
                
        except:
            msg = f"An error occurred while preprocessing station {StationFullName} for day {date}. Skipping day.\n"
            msg += "Trace details:\n"
            msg += f"  - StationFullName : {StationFullName}\n"
            msg += f"  - date : {date}"
            msg += f"  - Frequence : {Frequence} Hz"
            msg += f"  - DirPathSave : {DirPathSave}"
            msg += f"  - FileSave : {FileSave}"
            msg += traceback.format_exc()
            add_log(msg, level="error")
