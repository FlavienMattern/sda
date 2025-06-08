################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Parameters for the package.

Module tracesParam
==================

.. topic:: traces.tracesParam

    This module provide the parameters of the package :mod:`traces`.

:Parameters: 

        **ListOfStations**: list
            The list of stations. Only traces which correspond to these stations are processed.
            
        **LoadDirectory**: str
            A path directory.  Only traces in this directory are processed.
        
        **SaveDirectory**: str
            A path directory. Traces processed are saved in this directory.
            
        **NewFrequence**: float
            The new frequency sampling of the traces processed. If there is no resampling,
            set None.
            
        **ComponentStation**: str
            A component of the station. Set only 'E', 'N' or 'Z'.
            Only traces which correspond to this component are processed.
            
        **FormatTraceSave**: str
            The format to save the trace. Set only 'npy' (for numpy array format) or 'mat' (for matlab format).
            
        **FirstDay**, **FirstYear**: int or str
            A julian day and a year.
            FirstDay and FirstYear compose the date 'FirstYear/FirstDay'.
            Only traces with date *after* this date are processed.

        **LastDay**, **LastYear**: int or str
            A julian day and a year.
            LastDay and LastYear compose the date 'LastYear/LastDay'.
            Only traces with date *after* this date are processed.
            
        **HasToMakeDictOfTraces**: boolean
            If True, built the dictionaries of traces for each date, before processing the traces.
            If False, treat the traces directly. That is suppose that the dictionaries of traces are
            already made.
            
            .. Note::
                
                If you do not know the value for **HasToMakeDictOfTraces**, set True.
        
"""
# import os
# #======DO NOT DELETE THIS LINE AND THE ONES BEFORE========


# ##DataPath
# DataPath = "/media/flavien/DATA/FLAVIEN/these/sample_short"


# ######
# # /!\ NEED TO BE CHANGED MANUALLY IF FILES ARE ORGANIZED DIFFERENTLY
# # ListOfStations = os.listdir(DataPath)
# ##ListOfStations
# ListOfStations = ['HOHE']
# ######

# ##LoadDirectory
# LoadDirectory = DataPath
# ##SaveDirectory
# SaveDirectory = "/media/flavien/DATA/FLAVIEN/these/xcorr/sandbox/RESULTS/EXP"
# try:
# 	os.mkdir(SaveDirectory)
# except:
# 	pass
# ##NewFrequence
# NewFrequence = 10
# ##ComponentStation
# ComponentStation = "Z"
# ##FormatTraceSave
# FormatTraceSave = "npy"
# ##FirstDay
# FirstDay = 1
# ##FirstYear
# FirstYear = 2019
# ##LastDay
# LastDay = 1
# ##LastYear
# LastYear = 2020
# ##HasToMakeDictOfTraces
# HasToMakeDictOfTraces = True
