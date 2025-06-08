################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Generators of couples traces and save path files.

Module correlationsGeneratorPath
================================


.. topic:: correlations.correlationsGeneratorPath

    Provide classes of generators in order to get the couple of traces for computing correlation. This define a hierarchy of classes, 
    induced by the cases of one list or two lists of stations:

    .. inheritance-diagram::
         InitGeneratorCoupleTraces
         GeneratorDateCoupleNotSaveOneListStation
         GeneratorDateArrayFirstStationAndNameSecondStationOneListStation
         GeneratorPathSaveDateCoupleArraysOneList
         GeneratorDateCoupleNotSaveTwoListsStation
         GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations
         GeneratorPathSaveDateCoupleArraysTwoLists
         :parts: 1
        
    * An instance of the class :class:`GeneratorPathSaveDateCoupleArraysOneList` provides a generator of all 
      necessaries informations for computing correlation for one sublist of stations.

    * An instance of the class :class:`GeneratorPathSaveDateCoupleArraysTwoLists` provides a generator of all 
      necessaries informations for computing correlation for two sublists of stations.

"""

import numpy
import os
# import correlationsExceptions
# import correlationsUtil
from sda.xcorr_noise.CorrelationModules import correlationsExceptions
from sda.xcorr_noise.CorrelationModules import correlationsUtil



class InitGeneratorCoupleTraces(object):
    """
    Get the attribute **ListOfDates** from the key 'param' of the dictionary kwargs.
    
    :Attribute:
        **ListOfDates**: list
            Defined in the module :mod:`correlations.correlationsGetParam`
        
    """
    def __init__(self, **kwargs):
        try:
            self.ListOfDates = kwargs['param'].ListOfDates
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='InitGeneratorCoupleTraces', ListMissingAttribute=['ListOfDates'])

class GeneratorDateCoupleNotSaveOneListStation(InitGeneratorCoupleTraces):
    """
    **A generator**
    
    Generate, for each date, for each couple of stations:
    
        * the directory to save the correlation.
        * the file name to save the correlation.
        * the date.
        * a first station of the list of stations.
        * a second station of the list of stations. 
    
    :Base class: :class:`InitGeneratorCoupleTraces`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **ListOfStations**: list
            Defined in the module :mod:`correlations.correlationsGetParam`.
            
        **LenListOfStations**: int
            The length of the list of stations *ListOfStations*.

    :Parameters:
    
        * An attribute 'ListOfStations' of a key 'param' of the dictionary kwargs.
        
        * A method 'getDirAndFileSaveCorrelation' of a key 'writer' of the dictionary kwargs in order to get
          the path file to save the correlation.
        
        
    """    
    
    def __init__(self, **kwargs):
        InitGeneratorCoupleTraces.__init__(self, **kwargs)
        try:
            self.ListOfStations = kwargs['param'].ListOfStations
            self.LenListOfStations = len(self.ListOfStations)
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateCoupleNotSaveOneListStation', ListMissingAttribute=['ListOfStations'])
        try:
            self.getDirAndFileSaveCorrelation = kwargs['writer'].getDirAndFileSaveCorrelation
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateCoupleNotSaveOneListStation', ListMissingMethod=['getDirAndFileSaveCorrelation'])

    def __iter__(self):
        noPathFirstStation = None
        for date in self.ListOfDates:
            for indexFisrtStation, FirstStation in enumerate(self.ListOfStations):
                indexSecondStation = indexFisrtStation
                while indexSecondStation < self.LenListOfStations:
                    SecondStation = self.ListOfStations[indexSecondStation]
                    DirSave, FileSave = self.getDirAndFileSaveCorrelation(date, FirstStation, SecondStation)
                    if not os.path.isfile(DirSave + FileSave):
                        noPathFirstStation = (yield DirSave, FileSave, date, FirstStation, SecondStation)
                    if noPathFirstStation == 'BadPathFirstStation':
                        indexSecondStation = self.LenListOfStations-1
                    else:
                        indexSecondStation += 1


        

class GeneratorDateArrayFirstStationAndNameSecondStationOneListStation(GeneratorDateCoupleNotSaveOneListStation):
    """
    **A generator**
    
    Generate, for each date, for each couple of stations:
    
        * the directory to save the correlation.
        * the file name to save the correlation.
        * the date.
        * an array correspond to the trace of the first station of the list of stations.
        * a second station of the list of stations. 
    
    :Base class: :class:`GeneratorDateCoupleNotSaveOneListStation`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **ComponentFirstStation**: str
            Defined in the module :mod:`correlations.correlationsGetParam`.
    
    :Parameters:
    
        * An attribute 'ComponentFirstStation' of a key 'param' of the dictionary kwargs.
        
        * A method 'getDirAndFileLoadTrace' of a key 'loader' of the dictionary kwargs in order to get
          the path file to load the first trace.
          
        * A method 'loadOneTrace' of a key 'loader' of the dictionary kwargs in order to load
          the first trace.
       
    """    

    def __init__(self, **kwargs):
        GeneratorDateCoupleNotSaveOneListStation.__init__(self, **kwargs)
        try:
            self.ComponentFirstStation = kwargs['param'].ComponentFirstStation
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateArrayFirstStationAndNameSecondStationOneListStation', ListMissingAttribute=['ComponentFirstStation'])
        try:
            self.getDirAndFileLoadTrace = kwargs['loader'].getDirAndFileLoadTrace
            self.loadOneTrace =  kwargs['loader'].loadOneTrace
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateArrayFirstStationAndNameSecondStationOneListStation', ListMissingMethod=['getDirAndFileLoadTrace', 'loadOneTrace'])
        
    def __iter__(self):
        genDateCoupleNotSave = GeneratorDateCoupleNotSaveOneListStation.__iter__(self)
        for DirSave, FileSave, date, FirstStation, SecondStation in genDateCoupleNotSave:
            try:
                if FirstStation == SecondStation:
                    path_acorr = True
                else:
                    path_acorr = False
                DirTrace, FileTrace = self.getDirAndFileLoadTrace(self.ComponentFirstStation, date, FirstStation, path_acorr)
                # DirTrace = DirTrace.replace(f"{os.sep}{os.sep}", f"{os.sep}")
                """For testing paths:
                if not FirstStation in ['232A', '233A']:
                    arrayFirstTrace = numpy.load(DirTrace + FileTrace)
                else:
                    arrayFirstTrace = DirTrace + FileTrace
                """
                arrayFirstTrace = self.loadOneTrace(DirTrace, FileTrace)
                #"""
                yield (DirSave, FileSave, date, arrayFirstTrace, SecondStation, FirstStation)
            except IOError as msg:
                genDateCoupleNotSave.send('BadPathFirstStation')
                print("Unable to read preprocessed file \n" + str(msg))
                pass


class GeneratorPathSaveDateCoupleArraysOneList(GeneratorDateArrayFirstStationAndNameSecondStationOneListStation):
    """
    **A generator**
    
    Generate, for each date, for each couple of stations:
    
        * the directory to save the correlation.
        * the file name to save the correlation.
        * the date.
        * an array correspond to the trace of the first station of the list of stations.
        * an array correspond to the trace of the second station of the list of stations.
    
    :Base class: :class:`GeneratorDateArrayFirstStationAndNameSecondStationOneListStation`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **ComponentSecondStation**: str
            Defined in the module :mod:`correlations.correlationsGetParam`.
    
    :Parameters:
    
        * An attribute 'ComponentSecondStation' of a key 'param' of the dictionary kwargs.
    """    
    def __init__(self, **kwargs):
        GeneratorDateArrayFirstStationAndNameSecondStationOneListStation.__init__(self, **kwargs)
        try:
            self.ComponentSecondStation = kwargs['param'].ComponentSecondStation
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorPathSaveDateCoupleArraysOneList', ListMissingAttribute=['ComponentSecondStation'])

    def __iter__(self):
        genDateArrayAStationB = GeneratorDateArrayFirstStationAndNameSecondStationOneListStation.__iter__(self)
        for DirSave, FileSave, date, arrayFirstTrace, SecondStation, FirstStation in genDateArrayAStationB:
            try:
                if FirstStation == SecondStation:
                    path_acorr = True
                else:
                    path_acorr = False
                DirTrace, FileTrace = self.getDirAndFileLoadTrace(self.ComponentSecondStation, date, SecondStation, path_acorr)
                arraySecondTrace = self.loadOneTrace(DirTrace, FileTrace)                #"""
                yield (DirSave, FileSave, date, arrayFirstTrace, arraySecondTrace)
            except IOError as msg:
                print("Unable to read preprocessed file \n" + str(msg))
                pass
                #print 'stationB: ' + str(msg)


class GeneratorPathSaveOneDateCoupleArraysOneList(GeneratorPathSaveDateCoupleArraysOneList):
    """
    **A generator**
    
    :Base class: :class:`GeneratorPathSaveDateCoupleArraysOneList`
        Inherits all attributes of the base class.
        
    Filter the value of the generator :class:`GeneratorPathSaveDateCoupleArraysOneList`.
    Yield the same value as the generator :class:`GeneratorPathSaveDateCoupleArraysOneList` excepted
    yield **None** instead of the file path (path, file) to save the **stack** correlation if the file path  will be identical at the next
    generation.
    
    See also the class :class:`correlations.correlationsUtil.LastNewValueGeneratorOfListIndex` in the module :mod:`doubletUtil` use
    for filtering.
    """
    def __init__(self, **kwargs):
        GeneratorPathSaveDateCoupleArraysOneList.__init__(self, **kwargs)
        
    def __iter__(self):
        genDateCoupleNotSaveOneListStation = GeneratorPathSaveDateCoupleArraysOneList.__iter__(self)
        #g = genDateCoupleNotSaveOneListStation
        g = correlationsUtil.LastNewValueGeneratorOfListIndex(genDateCoupleNotSaveOneListStation, [2],'NoneValues')
        for DirSave, FileSave, date, FirstStation, SecondStation in g:
            yield (DirSave, FileSave, date, FirstStation, SecondStation)

class GeneratorDateCoupleNotSaveTwoListsStation(InitGeneratorCoupleTraces):
    """
    **A generator**
    
    Generate, for each date, for each couple of stations:
    
        * the directory to save the correlation.
        * the file name to save the correlation.
        * the date.
        * a first station of the first list of stations.
        * a second station of the second list of stations. 
    
    :Base class: :class:`InitGeneratorCoupleTraces`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **FirstListOfStations**: list
            Defined in the module :mod:`correlations.correlationsGetParam`.
        
        **SecondListOfStations**: list
            Defined in the module :mod:`correlations.correlationsGetParam`.
            

    :Parameters:
    
        * An attribute 'FirstListOfStations' of a key 'param' of the dictionary kwargs.
        
        * An attribute 'SecondListOfStations' of a key 'param' of the dictionary kwargs.
        
        * A method 'getDirAndFileSaveCorrelation' of a key 'writer' of the dictionary kwargs in order to get
          the path file to save the correlation.
        
        
    """    
    def __init__(self, **kwargs):
        InitGeneratorCoupleTraces.__init__(self, **kwargs)
        try:
            self.FirstListOfStations = kwargs['param'].FirstListOfStations
            self.SecondListOfStations = kwargs['param'].SecondListOfStations
            self.LenFirstListOfStations = len(self.FirstListOfStations)
            self.LenSecondListOfStations = len(self.SecondListOfStations)
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateCoupleNotSaveTwoListsStation', ListMissingAttribute=['FirstListOfStations', 'SecondListOfStations'])
        try:
            self.getDirAndFileSaveCorrelation = kwargs['writer'].getDirAndFileSaveCorrelation
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateCoupleNotSaveTwoListsStation', ListMissingMethod=['getDirAndFileDictOfDoublet'])

    def __iter__(self):
        noPathFirstStation = None
        for date in self.ListOfDates:
            for FirstStation in self.FirstListOfStations:
                indexSecondStation = 0
                while indexSecondStation < self.LenSecondListOfStations:
                    SecondStation = self.SecondListOfStations[indexSecondStation]
                    DirSave, FileSave = self.getDirAndFileSaveCorrelation(date, FirstStation, SecondStation)
                    if not os.path.isfile(DirSave + FileSave):
                        noPathFirstStation = (yield DirSave, FileSave, date, FirstStation, SecondStation)
                    if noPathFirstStation == 'BadPathFirstStation':
                        indexSecondStation = self.LenSecondListOfStations-1
                    else:
                        indexSecondStation += 1

class GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations(GeneratorDateCoupleNotSaveTwoListsStation):
    """
    **A generator**
    
    Generate, for each date, for each couple of stations:
    
        * the directory to save the correlation.
        * the file name to save the correlation.
        * the date.
        * an array correspond to the trace of the first station of the first list of stations.
        * a second station of the second list of stations. 
    
    :Base class: :class:`GeneratorDateCoupleNotSaveTwoListsStation`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **ComponentFirstStation**: str
            Defined in the module :mod:`correlations.correlationsGetParam`.
    
    :Parameters:
    
        * An attribute 'ComponentFirstStation' of a key 'param' of the dictionary kwargs.
        
        * A method 'getDirAndFileLoadTrace' of a key 'loader' of the dictionary kwargs in order to get
          the path file to load the first trace.
          
        * A method 'loadOneTrace' of a key 'loader' of the dictionary kwargs in order to load
          the first trace.
       
    """    
    def __init__(self, **kwargs):
        GeneratorDateCoupleNotSaveTwoListsStation.__init__(self, **kwargs)
        try:
            self.ComponentFirstStation = kwargs['param'].ComponentFirstStation
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations', ListMissingAttribute=['ComponentFirstStation'])
        try:
            self.getDirAndFileLoadTrace = kwargs['loader'].getDirAndFileLoadTrace
            self.loadOneTrace =  kwargs['loader'].loadOneTrace
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations', ListMissingMethod=['getDirAndFileLoadTrace', 'loadOneTrace'])
        
    def __iter__(self):
        genDateCoupleNotSave = GeneratorDateCoupleNotSaveTwoListsStation.__iter__(self)
        for DirSave, FileSave, date, FirstStation, SecondStation in genDateCoupleNotSave:
            try:
                if FirstStation == SecondStation:
                    path_acorr = True
                else:
                    path_acorr = False
                DirTrace, FileTrace = self.getDirAndFileLoadTrace(self.ComponentFirstStation, date, FirstStation, path_acorr)
                """For testing paths:
                if not FirstStation in ['332A', '333A']:
                    arrayFirstTrace = numpy.load(DirTrace + FileTrace)
                else:
                    arrayFirstTrace = DirTrace + FileTrace
                """
                arrayFirstTrace = self.loadOneTrace(DirTrace, FileTrace)
                #"""
                yield (DirSave, FileSave, date, arrayFirstTrace, SecondStation, FirstStation)
            except IOError as msg:
                genDateCoupleNotSave.send('BadPathFirstStation')
                #print 'stationA: ' + str(msg)


class GeneratorPathSaveDateCoupleArraysTwoLists(GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations):
    """
    **A generator**
    
    Generate, for each date, for each couple of stations:
    
        * the directory to save the correlation.
        * the file name to save the correlation.
        * the date.
        * an array correspond to the trace of the first station of the first list of stations.
        * an array correspond to the trace of the second station of the second list of stations.
    
    :Base class: :class:`GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **ComponentSecondStation**: str
            Defined in the module :mod:`correlations.correlationsGetParam`.
    
    :Parameters:
    
        * An attribute 'ComponentSecondStation' of a key 'param' of the dictionary kwargs.
        
    """    
    def __init__(self, **kwargs):
        GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations.__init__(self, **kwargs)
        try:
            self.ComponentSecondStation = kwargs['param'].ComponentSecondStation
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='GeneratorPathSaveDateCoupleArraysTwoLists', ListMissingAttribute=['ComponentSecondStation'])
        
    def __iter__(self):
        genDateArrayAStationB = GeneratorDateArrayFirstStationAndNameSecondStationTwosListsStations.__iter__(self)
        for DirSave, FileSave, date, arrayFirstTrace, SecondStation, FirstStation in genDateArrayAStationB:
            try:
                if FirstStation == SecondStation:
                    path_acorr = True
                else:
                    path_acorr = False
                DirTrace, FileTrace = self.getDirAndFileLoadTrace(self.ComponentSecondStation, date, SecondStation)
                """For testing paths:
                if not SecondStation in ['U32A', 'U34A', 'V20A']:
                    arraySecondTrace = numpy.load(DirTrace + FileTrace)
                else:
                    arraySecondTrace = DirTrace + FileTrace
                """
                arraySecondTrace = self.loadOneTrace(DirTrace, FileTrace)
                #"""
                yield (DirSave, FileSave, date, arrayFirstTrace, arraySecondTrace)
            except IOError as msg:
                pass
                #print 'stationB: ' + str(msg)

class GeneratorPathSaveOneDateCoupleArraysTwoLists(GeneratorPathSaveDateCoupleArraysTwoLists):
    """
    **A generator**
    
    :Base class: :class:`GeneratorPathSaveDateCoupleArraysTwoLists`
        Inherits all attributes of the base class.
        
    Filter the value of the generator :class:`GeneratorPathSaveDateCoupleArraysTwoLists`.
    Yield the same value as the generator :class:`GeneratorPathSaveDateCoupleArraysTwoLists` excepted
    yield **None** instead of the file path (path, file) to save the **stack** correlation if the file path  will be identical at the next
    generation.
    
    See also the class :class:`correlations.correlationsUtil.LastNewValueGeneratorOfListIndex` in the module :mod:`doubletUtil` use
    for filtering.
    """
    def __init__(self, **kwargs):
        GeneratorPathSaveDateCoupleArraysTwoLists.__init__(self, **kwargs)
        
    def __iter__(self):
        genDateCoupleNotSaveOneListStation = GeneratorPathSaveDateCoupleArraysTwoLists.__iter__(self)
        #g = genDateCoupleNotSaveOneListStation
        g = correlationsUtil.LastNewValueGeneratorOfListIndex(genDateCoupleNotSaveOneListStation, [2],'NoneValues')
        for DirSave, FileSave, date, FirstStation, SecondStation in g:
            yield (DirSave, FileSave, date, FirstStation, SecondStation)

if __name__ == '__main__':
    pass