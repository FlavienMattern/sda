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
from sda.process.xcorr_noise.PreProcessingModules.TraceModules import tracesGetParam, tracesExceptions, tracesGeneratorPath, tracesWriter, tracesTreatment, tracesDictOfTraces
from sda.core.logs import add_log


def treatTracesFromDirectory(config):
    """
    See the general specification.
    """
    try:
        parameters = tracesGetParam.Param(config)
        traceMakeDicts = tracesDictOfTraces.DictOfTraces(config, param=parameters)
    except tracesExceptions.ExceptionTraces as msg:
        # print(msg)
        raise
    
    if os.path.isdir(parameters.SaveDirectory):
        sys.stdout.flush()
    
    if parameters.HasToMakeDictOfTraces:
        if os.path.isdir(traceMakeDicts.PathDirectoryTemp):
            add_log(f"Temporary directory already exists: {traceMakeDicts.PathDirectoryTemp}. Files will be overwritten.", level="warning")
        traceMakeDicts.writeDirectory(traceMakeDicts.PathDirectoryTemp)

        if os.path.isdir(traceMakeDicts.PathDirDictsOfTraces):
            add_log(f"DictOfTraces directory already exists: {traceMakeDicts.PathDirDictsOfTraces}. Files will be overwritten.", level="warning")
        traceMakeDicts.writeDirectory(traceMakeDicts.PathDirDictsOfTraces)
        
        add_log(f"Building TempPickle: temporary metdata in {traceMakeDicts.PathDirectoryTemp}", level="info")
        traceMakeDicts.makeTempPickleFilesOfDictOfTraces()

        add_log(f"Building DictOfTraces: daily metdata in {traceMakeDicts.PathDirDictsOfTraces}", level="info")
        traceMakeDicts.makeDictOfTraceOfOneDayFromTempFilesDictOfTraces()

        add_log(f"Removing Temporary Directory.", level="info")
        traceMakeDicts.removeTemporaryDirectory()
