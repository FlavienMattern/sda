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
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesGetParam
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesExceptions
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesGeneratorPath
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesWriter
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesTreatment
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesDictOfTraces



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
        traceMakeDicts.writeDirectory(traceMakeDicts.PathDirectoryTemp)
        traceMakeDicts.writeDirectory(traceMakeDicts.PathDirDictsOfTraces)
        traceMakeDicts.makeTempPickleFilesOfDictOfTraces()
        traceMakeDicts.makeDictOfTraceOfOneDayFromTempFilesDictOfTraces()
        traceMakeDicts.removeTemporaryDirectory()


if __name__ == '__main__':
    treatTracesFromDirectory(config)
