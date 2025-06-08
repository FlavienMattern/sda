################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Main functionality: provide a function for computing correlations.

Module correlationsMain
=======================

Provide a function :func:`makeCorrFromDirectoryTraces` in order to make all
the correlations of the traces (see :doc:`correlationsOverview`).

In order to run this function, it is necessary to set the parameters in the module :mod:`correlations.correlationsParam`
and to define in line parameters.

Running the module:
-------------------

.. topic:: Requirement
    
    The architecture of traces to load must be:
    
    * Either exactly the architecture of files induced by
      the output of the module :mod:`traces.tracesMain` defined in the package :mod:`traces`,
      i.e.:
        
        LoadDirectory -> Component -> Year -> Day -> Station.
    
      (The LoadDirectory for correlations is the SaveDirectory for the traces.)
    
    * Or either an architecture where Year -> Day directories are replace by a date 
      in a list of dates (an attribute 'ListOfDates') defined in the module :mod:`correlations.correlationsParam`, i.e.:
        
        LoadDirectory -> Component -> date -> Station.


For whisper users, suppose we have the directory **correlations** (the package).
For computing all the correlations simply type:

.. code-block:: python

    $ cd correlations
    $ python2.7 correlationsMain.py oneList LoadDirectory SaveDirectory ComponentFirstStation ComponentSecondStation 1 0 1 0

**Decentralized options**:

* (**One List of stations**):
  If you want to divide the list of dates of **5 equal sublists** and the list of stations of **11 sublists**.
  Moreover if you want to compute the correlations for the **third sublist** (index 2) of dates and the **fifth sublist**
  (index 4) of stations, type:
    
    .. code-block:: python
    
        $ cd correlations
        $ python2.7 correlationsMain.py oneList LoadDirectory SaveDirectory ComponentFirstStation ComponentSecondStation 5 2 11 4

* (**Two Lists of stations**):
  If you want to divide the list of dates of **5** equal sublists and the list of stations of **11** sublists.
  Moreover if you want to compute the correlations for the **third sublist** (index 2) of dates and between the **first sublist**
  (index 0) of stations and the **tenth sublist** (index 9) of stations, type:
    
    .. code-block:: python
    
        $ cd correlations
        $ python2.7 correlationsMain.py twoLists LoadDirectory SaveDirectory  ComponentFirstStation ComponentSecondStation 5 2 11 0 9


Python necessary libraries:
---------------------------

* python2.7
* scipy
* numpy


More precisely we use at the present time:

.. code-block:: python

    >>> import numpy
    >>> numpy.__version__
    '1.5.0'
    >>> import scipy
    >>> scipy.__version__
    '0.9.0.dev6939'




"""
import sys
import time
import correlationsGetParam
import correlationsExceptions
import correlationsCorrelation
import correlationsGeneratorPath
import correlationsWriter
import correlationsLoader

def makeCorrFromDirectoryTraces():
    try:
        parameters = correlationsGetParam.ParamWithLastDateCompute()
        print(parameters)
        correlation = correlationsCorrelation.Correlation()
        print(correlation)
        
        if parameters.FormatSave == 'mat':
            writeCorr = correlationsWriter.WriterOneCorrelationMat(parameters)
        elif parameters.FormatSave == 'npy':
            writeCorr = correlationsWriter.WriterOneCorrelationNpy(parameters)
        
        if parameters.FormatTrace == 'mat':
            loadTrace = correlationsLoader.LoaderOneTraceMat(parameters)
        elif parameters.FormatTrace == 'npy':
            loadTrace = correlationsLoader.LoaderOneTraceNpy(parameters)
    
    except correlationsExceptions.ExceptionCorrelations as msg:
        print(msg)
        raise
    
    if parameters.TypeListStations == 'oneList':
        generatorCouple = correlationsGeneratorPath.GeneratorPathSaveOneDateCoupleArraysOneList(param=parameters, loader=loadTrace, writer=writeCorr)
    elif parameters.TypeListStations == 'twoLists':
        generatorCouple = correlationsGeneratorPath.GeneratorPathSaveOneDateCoupleArraysTwoLists(param=parameters, loader=loadTrace, writer=writeCorr)
    else:
        sys.exit()
    
    BeginTimeTotal = time.time()
    BeginTimeDate = time.time()
    NumberOfCorrOneDate = 0
    NumberOfCorrTotal = 0
    
    for DirSave, FileSave, date, firstTrace, secondTrace in generatorCouple:
        #"""
        corr = correlation.makeCorrWithMaxlag(firstTrace, secondTrace)
        writeCorr.writeOneCorrelation(DirSave, FileSave, corr)
        NumberOfCorrOneDate += 1
        #"""
        if date is not None:
            print('DATE TIME: ', end=' ')
            print("Time.time to compute the " + str(NumberOfCorrOneDate) +  " correlations: ", end=' ')
            print(time.time() - BeginTimeDate, end=' ')
            print('for the date: ' + str(date))
            sys.stderr.flush()
            sys.stdout.flush()
            parameters.writeLastDateCompute(date)
            BeginTimeDate = time.time()
            NumberOfCorrTotal += NumberOfCorrOneDate
            NumberOfCorrOneDate = 0

    print("TOTAL Time.time to compute all the " + str(NumberOfCorrTotal) +  " correlations: ", end=' ')
    print(time.time()-BeginTimeTotal)

if __name__ == '__main__':
    makeCorrFromDirectoryTraces()
