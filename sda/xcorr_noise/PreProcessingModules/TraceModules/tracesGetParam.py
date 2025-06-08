################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Get the parameters.

Module tracesGetParam
=====================

.. topic:: traces.tracesGetParam

    Provide a class :class:`param` in order to get the parameters
    defined in the module :mod:`TraceModules.tracesParam`.
    
"""

import os
# import sys
# import TraceModules.tracesParam
# import TraceModules.tracesUtil
# import TraceModules.tracesExceptions
# import TraceModules.tracesTestParam

from sda.xcorr_noise.PreProcessingModules.TraceModules import tracesParam
from sda.xcorr_noise.PreProcessingModules.TraceModules import tracesUtil
from sda.xcorr_noise.PreProcessingModules.TraceModules import tracesExceptions
from sda.xcorr_noise.PreProcessingModules.TraceModules import tracesTestParam



class Param(object):
    """
    Get parameters in order to treat traces (see the attributes).
    
    
    :Attributes:
        
        **ListOfDates**: list
            The list of dates induced by parameters FirstDay, FirstYear, LastDay and
            LastYear defined in the module :mod:`TraceModules.tracesParam`.
        
        **ListOfStations**: list
            Defined in the module :mod:`TraceModules.tracesParam`.

        **FormatTraceSave**: str
            Defined in the module :mod:`TraceModules.tracesParam`.
            
        **LoadDirectory**: str
            Defined in the module :mod:`TraceModules.tracesParam`.
        
        **SaveDirectory**: str
            Defined in the module :mod:`TraceModules.tracesParam`.
            
        **NewFrequence**: float
            Defined in the module :mod:`TraceModules.tracesParam`.
    
        **ComponentStation**: str
            Defined in the module :mod:`TraceModules.tracesParam`.
        
        **PathDirDictsOfTraces**: str
            The path directory of the pickle file contains the dictionaries of traces.
            
        **PrefixNameFileDictsOfTraces**: str
            The prefix of the pickle file contains the dictionaries of traces.
    
    """

    def __init__(self, config):

        self.testParam = tracesTestParam.TestValueParam()
        self.getFormatSaveTrace()
        self.getListOfDates(config)
        self.getListOfStations(config)
        self.getLoadDirectory(config)
        self.getSaveDirectory(config)
        self.getComponentStation(config)
        self.NewFrequence = self.getNewFrequence(config)
        self.__getPathDictOfTrace()
        self.__getHasToMakeDictsOfTraces(config) 
        
    def getFormatSaveTrace(self):
        try:
            # self.FormatTraceSave = TraceModules.tracesParam.FormatTraceSave
            self.FormatTraceSave = "npy"
            if not self.testParam.isGoodFormatSave(FormatTraceSave = self.FormatTraceSave):
                raise tracesExceptions.ErrorParamFromParamFile('FormatTraceSave')
        except (AttributeError, ValueError):
            raise tracesExceptions.ErrorParamFromParamFile('FormatTraceSave')
    
    def getListOfDates(self, config):
        self.ListOfDates = []
        try:
            # FirstDay = int(TraceModules.tracesParam.FirstDay)
            # FirstYear = int(TraceModules.tracesParam.FirstYear)
            # LastDay = int(TraceModules.tracesParam.LastDay)
            # LastYear = int(TraceModules.tracesParam.LastYear)
            FirstDay = int(config["FirstDay"])
            FirstYear = int(config["FirstYear"])
            LastDay = int(config["LastDay"])
            LastYear = int(config["LastYear"])
            if not self.testParam.isGoodJulianDayOfYear(FirstDay, FirstYear) and self.testParam.isGoodJulianDayOfYear(LastDay, LastYear):
                raise tracesExceptions.ErrorParamFromParamFile('ListOfDates')
            elif not self.testParam.isGoodOrderDates(FirstDay, FirstYear, LastDay, LastYear):
                raise tracesExceptions.ErrorParamFromParamFile('badOrderDates')
            self.ListOfDates = list(tracesUtil.listDateIterator(str(FirstDay), str(FirstYear), str(LastDay), str(LastYear)))
            
        
        except (AttributeError, ValueError):
            raise tracesExceptions.ErrorParamFromParamFile('ListOfDates')
        return sorted(self.ListOfDates)

    def getListOfStations(self, config):
        self.ListOfStations = sorted(config["stations"])
        # if  hasattr(TraceModules.tracesParam, 'ListOfStations') and isinstance(TraceModules.tracesParam.ListOfStations, list) and TraceModules.tracesParam.ListOfStations:
        #     self.ListOfStations = sorted(TraceModules.tracesParam.ListOfStations)
        # else:
        #     raise TraceModules.tracesExceptions.ErrorParamFromParamFile('ListOfStations')

    def getNewFrequence(self, config):
        return config["NewFrequence"]
        # if  hasattr(TraceModules.tracesParam, 'NewFrequence') and (isinstance(TraceModules.tracesParam.NewFrequence, float) or  isinstance(TraceModules.tracesParam.NewFrequence, int)):
        #     return float(TraceModules.tracesParam.NewFrequence)
        # else:
        #     raise TraceModules.tracesExceptions.ErrorParamFromParamFile('NewFrequence')

    def getLoadDirectory(self, config):
        self.LoadDirectory = config["DataPath"]
        # try:
        #     self.LoadDirectory = TraceModules.tracesParam.LoadDirectory
        #     if not self.testParam.isGoodLoadDirectory(LoadDirectory = self.LoadDirectory):
        #         raise TraceModules.tracesExceptions.ErrorParamFromParamFile('LoadDirectory')
        # except (AttributeError, ValueError):
        #     raise TraceModules.tracesExceptions.ErrorParamFromParamFile('LoadDirectory')
    
    def getSaveDirectory(self, config): 
        try:
            # self.SaveDirectory = TraceModules.tracesParam.SaveDirectory
            self.SaveDirectory = config["SaveDirectory"]
            if not self.testParam.isGoodSaveDirectory(SaveDirectory = self.SaveDirectory):
                raise tracesExceptions.ErrorParamFromParamFile('SaveDirectory')
        except (AttributeError, ValueError):
            raise tracesExceptions.ErrorParamFromParamFile('SaveDirectory')

    def getComponentStation(self, config):
        try:
            # self.ComponentStation = TraceModules.tracesParam.ComponentStation
            self.ComponentStation = config["ComponentStation"]
            if not self.testParam.isGoodComponent(ComponentStation = self.ComponentStation):
                raise tracesExceptions.ErrorParamFromParamFile('ComponentStation')
        except (AttributeError, ValueError):
            raise tracesExceptions.ErrorParamFromParamFile('ComponentStation')
        
    def __getPathDictOfTrace(self):
        self.PrefixNameFileDictsOfTraces = 'DictOfTracesOneDay_'
        self.PathDirDictsOfTraces = self.SaveDirectory + os.sep + 'DictsOfTraces' + os.sep

    def __getHasToMakeDictsOfTraces(self, config):
        self.HasToMakeDictOfTraces = config["HasToMakeDictOfTraces"]
        # try:
        #     self.HasToMakeDictOfTraces = TraceModules.tracesParam.HasToMakeDictOfTraces
        # except (AttributeError, ValueError):
        #     pass

    def getDirAndFileDictOfDoublet(self, day, year):
        """
        Return the path file of the dictionary of traces for a date (i.e. the day and the year).
        """
        return self.PathDirDictsOfTraces + self.PrefixNameFileDictsOfTraces + year + '_' + day
    
    def __repr__(self):
        StringParamInline = 'FormatTraceSave: ' + self.FormatTraceSave + '\n'
        StringParamInline += 'LoadDirectory: ' + self.LoadDirectory + '\n'
        StringParamInline += 'SaveDirectory: ' + self.SaveDirectory + '\n'
        StringParamInline += 'ComponentStation: ' + self.ComponentStation + '\n'
        StringParamInline += 'ListOfDates: ' + str(self.ListOfDates) + '\n'
        StringParamInline += 'ListOfStations: ' + str(self.ListOfStations) + '\n'
        StringParamInline += 'NewFrequence: ' + str(self.NewFrequence) + '\n'
        StringParamInline += 'PrefixNameFileDictsOfTraces: ' + str(self.PrefixNameFileDictsOfTraces) + '\n'
        StringParamInline += 'PathDirDictsOfTraces: ' + str(self.PathDirDictsOfTraces) + '\n'
        return StringParamInline

if __name__ == '__main__':
    try:
        p=Param()
    except tracesExceptions.ErrorParam as msg:
        print(msg)
