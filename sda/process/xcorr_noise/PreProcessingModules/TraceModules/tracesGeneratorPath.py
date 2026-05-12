################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Generators of traces and their informations.

Module tracesGeneratorPath
==========================


.. topic:: traces.tracesGeneratorPath

    Provide classes of generators in order to get the trace to be treated. This define a hierarchy of classes:

    .. inheritance-diagram::
        generatorDatePathFileDictOfTraces 
        generatorDateDictOfTracesOneComponent 
        generatorPathSaveStationListFilesStationOneDay 
        generatorOneDatePathSaveStationListFilesStationOneDay
        generatorArrayBeTreatFrequenceAndPathSave
        :parts: 1
        
    An instance of the class :class:`generatorArrayBeTreatFrequenceAndPathSave` provides a generator of all 
    necessary informations for processing a trace and save it.

"""

import sys
import os
import pickle
import obspy.core
import numpy
import scipy.fftpack
import scipy.signal
from datetime import datetime, timedelta
from sda.process.xcorr_noise.PreProcessingModules.TraceModules import tracesExceptions, tracesUtil
from sda.core.logs import add_log
import traceback



class generatorDatePathFileDictOfTraces(object):
    """
    **A generator**
    
    Generate, for each date:
    
        * the date 
        * the file path of the dictionary of traces.
    
    :Attributes:
        
        **PathDirDictsOfTraces**: str
            Defined in the module :mod:`traces.tracesGetParam`
            
        **PrefixNameFileDictsOfTraces**: str 
            Defined in the module :mod:`traces.tracesGetParam`
    """
    def __init__(self, **kwargs):
        try:
            self.PathDirDictsOfTraces = kwargs['param'].PathDirDictsOfTraces
            self.PrefixNameFileDictsOfTraces = kwargs['param'].PrefixNameFileDictsOfTraces
            self.ListOfDates = kwargs['param'].ListOfDates
            self.LenTrace = kwargs['config']["LenTrace"]
            self.NewFrequence = kwargs['config']["NewFrequence"]
            # self.ListOfDates = ["{}/{:03d}".format(cur_year,cur_day)]
            
        except AttributeError:
            raise  tracesExceptions.ErrorParamAttribute(classBadAttribute='generatorDatePathFileDictOfTraces', ListMissingAttribute=['PathDirDictsOfTraces', 'PrefixNameFileDictsOfTraces', 'ListOfDates'])
        
        try:
            self.getDirAndFileDictOfDoublet =  kwargs['param'].getDirAndFileDictOfDoublet
        except AttributeError:
            raise tracesExceptions.ErrorParamAttribute(classBadAttribute='generatorDatePathFileDictOfTraces', ListMissingMethod=['getDirAndFileDictOfDoublet'])

    def __iter__(self):
        for date in self.ListOfDates:
            year = date.split(os.sep)[0]
            day = date.split(os.sep)[1]
            FilePickle = self.getDirAndFileDictOfDoublet(day, year)
            if os.path.isfile(FilePickle):
                yield (date, FilePickle)
            else:
                pass
                
class generatorDateDictOfTracesOneComponent(generatorDatePathFileDictOfTraces):
    """
    **A generator**
    
    Generate, for each date: 
    
        * the date 
        * the dictionary of traces for one component
    
    :Base class: :class:`generatorDatePathFileDictOfTraces`
        Inherits all attibutes of the base class.
    
    :Attributes:
        
        **ComponentStation**: str
            Defined in the module :mod:`traces.tracesGetParam`
    """
    def __init__(self, **kwargs):
        generatorDatePathFileDictOfTraces.__init__(self, **kwargs)
        try:
            self.ComponentStation = kwargs['param'].ComponentStation
        except AttributeError:
            raise  tracesExceptions.ErrorParamAttribute(classBadAttribute='generatorDateDictOfTracesOneComponent', ListMissingAttribute=['ComponentStation'])
        
    def __iter__(self):
        genDatePathFileDictOfTraces = generatorDatePathFileDictOfTraces.__iter__(self)
        for date, FilePickle in genDatePathFileDictOfTraces:
            with open(FilePickle, 'rb') as fileDictTraces:
                DictOfTracesOneDay = pickle.load(fileDictTraces)
                DictOfTracesOneDayOneCompo = self.__fromDictTraceStationToDictTracesStationOneCompo(DictOfTracesOneDay, self.ComponentStation)
                yield (date, DictOfTracesOneDayOneCompo)

    def __fromDictTraceStationToDictTracesStationOneCompo(self, DictOfTraces, Component):
        DictTracesOneCompo = {}
        for station in list(DictOfTraces.keys()):
            try:
                DictTracesOneCompo[station] = DictOfTraces[station][Component]
            except:
                pass
        return DictTracesOneCompo

class generatorPathSaveStationListFilesStationOneDay(generatorDateDictOfTracesOneComponent):
    """
    **A generator**
    
    Generate, for each date and each station:
    
        * the date
        * the station
        * the path file to save the treatment
        * the list of couples (file, index of a trace in the file), i.e. all the pieces of trace for the date and the station.
    
    .. Note::
        
        * If the trace was already treated (More precisely, the path file to save the treatment already exists), it is not generate.
        * See the stream object defined by obsy.core for the index notion, http://docs.obspy.org/packages/autogen/obspy.core.stream.html.
        
    
    :Base class: :class:`generatorDateDictOfTracesOneComponent`
        Inherits all attibutes of the base class.
        
    :Attributes:
        
        **ListOfStations**: list
            Defined in the module :mod:`traces.tracesGetParam`
    """
    def __init__(self, **kwargs):
        generatorDateDictOfTracesOneComponent.__init__(self, **kwargs)
        try:
            self.ListOfStations = kwargs['param'].ListOfStations
        except AttributeError:
            raise  tracesExceptions.ErrorParamAttribute(classBadAttribute='generatorPathSaveStationListFilesStationOneDay', ListMissingAttribute=['ListOfStations', 'SaveDirectory', 'FormatTraceSave'])
        try:
            self.getNameDirAndFileSave = kwargs['writer'].getNameDirAndFileSave
        except AttributeError:
            raise tracesExceptions.ErrorParamAttribute(classBadAttribute='generatorPathSaveStationListFilesStationOneDay', ListMissingMethod=['getNameDirAndFileSave'])
    
    def __iter__(self):
        genDateDictOfTracesOneComponent = generatorDateDictOfTracesOneComponent.__iter__(self)
        for date, DictOfTracesOneDayOneCompo in genDateDictOfTracesOneComponent:
            for station in self.ListOfStations:
                DirPathSave, FileSave = self.getNameDirAndFileSave(date, station)
                if not os.path.isfile(DirPathSave + FileSave):
                    if list(DictOfTracesOneDayOneCompo.keys()):
                        if station in DictOfTracesOneDayOneCompo:
                            ListFileStationCompoOneDayWithIndex = []
                            for infoTrace in DictOfTracesOneDayOneCompo[station]:
                                for idx_trace in range(infoTrace['ntrace']):
                                    ListFileStationCompoOneDayWithIndex.append((infoTrace['nameFile'], idx_trace, infoTrace['channel']))
                            
                            yield (date, station, DirPathSave, FileSave, ListFileStationCompoOneDayWithIndex)


class generatorOneDatePathSaveStationListFilesStationOneDay(generatorPathSaveStationListFilesStationOneDay):
    """
    **A generator**
    
    :Base class: :class:`generatorPathSaveStationListFilesStationOneDay`
        Inherits all attributes of the base class.
        
    Filter the value of the generator :class:`generatorPathSaveStationListFilesStationOneDay`.
    Yield the same value as the generator :class:`generatorPathSaveStationListFilesStationOneDay` excepted
    yield **None** instead of the date if the date  will be identical at the next generation.
    
    See also the class :class:`traces.TraceModules.tracesUtil.LastNewValueGeneratorOfListIndex` in the module :mod:`doubletUtil` use
    for filtering.
    """
    def __init__(self, **kwargs):
        generatorPathSaveStationListFilesStationOneDay.__init__(self, **kwargs)
        
    def __iter__(self):
        generatorOneDatePathSaveStationListFilesStationOneDay = generatorPathSaveStationListFilesStationOneDay.__iter__(self)
        g = tracesUtil.LastNewValueGeneratorOfListIndex(generatorOneDatePathSaveStationListFilesStationOneDay, [0],'NoneValues')
        for date, station, DirPathSave, FileSave, ListFileStationCompoOneDayWithIndex in g:
            DirSave_split = DirPathSave.split(os.sep)
            if DirSave_split[-1] == "": DirSave_split = DirSave_split[:-1]
            date = DirSave_split[-2] + "/" + DirSave_split[-1]
            yield (date, station, DirPathSave, FileSave, ListFileStationCompoOneDayWithIndex)

class generatorArrayBeTreatFrequenceAndPathSave(generatorOneDatePathSaveStationListFilesStationOneDay):
    """
    **A generator**
    
    Generate, for each date and each station:
    
        * the date
        * the trace to treated
        * the frequency of the sampling
        * the path file to save the treatment
    
    :Base class: :class:`generatorOneDatePathSaveStationListFilesStationOneDay`
        Inherits all attibutes of the base class.
        
    :Attributes:
        
        **station**: str
            The name of a station.
             
        **ListFileStationCompoOneDayWithIndex**: list
            The list of couples (file, index of the trace), all the pieces of trace for the date and the station.
        
        **Frequency**: float
            The frequency of the longest piece of trace among pieces of traces defined by *ListFileStationCompoOneDayWithIndex*.
        
        **TraceToTreated**: numpy array 
            Contains all the pieces of the trace for a date and a station, otherwise the value is zero.
            There is also a time correction (induced by the difference between the startime and the sampling rate).

        **DurationTraceSave**:int
            Number of points of the array to treat.
        
    """
    def __init__(self, **kwargs):
        generatorOneDatePathSaveStationListFilesStationOneDay.__init__(self, **kwargs)
    
    def __iter__(self):
        genDateDictOfTracesOneComponent = generatorOneDatePathSaveStationListFilesStationOneDay.__iter__(self)
        for date, station, DirPathSave, FileSave, ListFileStationCompoOneDayWithIndex in genDateDictOfTracesOneComponent:
            self.station = station
            self.ListFileStationCompoOneDayWithIndex = ListFileStationCompoOneDayWithIndex
            self.BestCode = self.selectBestChannelCode()

            ###################################################################################################
            # DEBUG THIS PART

            self.Frequency, IndexLongestTrace = self.giveFrequenceAndIndexFromTheLongestTrace(date)

            ###################################################################################################
            self.DurationTraceSave = int(float(self.Frequency)*86400)
            self.TraceToTreated = numpy.zeros(self.DurationTraceSave, dtype='float')
            self.StationFullName = ""
            self.__StartDateTimeTrace = self.makeArrayToTreatAndGiveStartTime(date)
            self.timeCorrectionTrace(station, date)

            yield (date, self.TraceToTreated, self.Frequency, DirPathSave, FileSave, self.StationFullName)

    def selectBestChannelCode(self):
        code_priority = ["HH","BH","MH","EH","LH","HL","BL","ML","EL","LL","SH","HN","BN","MN","EN","LN","SN"]
        BestCode = ""
        for infile, indexTrace, channel in self.ListFileStationCompoOneDayWithIndex:
            code = channel[:2]
            if BestCode == "":
                BestCode = code
            else:
                lvlBestCode = numpy.argwhere(BestCode == numpy.array(code_priority))
                lvlCode = numpy.argwhere(code == numpy.array(code_priority))
                if len(lvlBestCode) == 0:
                    lvlBestCode = 999
                else:
                    lvlBestCode = lvlBestCode[0][0]
                if len(lvlCode) == 0:
                    lvlCode = 999
                else:
                    lvlCode = lvlCode[0][0]
                if lvlCode < lvlBestCode:
                    BestCode = code
        
        return BestCode
        
    def giveFrequenceAndIndexFromTheLongestTrace(self, date):
        
        starttime = datetime.strptime(date, "%Y/%j")
        endtime = starttime + timedelta(seconds=int(self.LenTrace/self.NewFrequence))
        
        FrequenceLongestTrace = 0.0
        BiggestLenTrace = 0.0
        IndexLongestTrace = 0
        LastFileOpened = ''
        for infile, indexTrace, channel in self.ListFileStationCompoOneDayWithIndex:
            if channel[:2] == self.BestCode:
                if not LastFileOpened == infile:
                    try:
                        Stream = obspy.core.read(infile, headonly=True)
                    except Exception as err:
                        msg = f"An error occurred while read file '{infile}'.\n"
                        msg += "Error details:\n"
                        msg += traceback.format_exc()
                        add_log(msg, level="error")
                        sys.exit()
                LastFileOpened = infile
                
                subStream = Stream[indexTrace]
                subStream.trim(obspy.core.UTCDateTime(starttime), obspy.core.UTCDateTime(endtime))
                FrequenceTrace = float(numpy.round(float(subStream.stats['sampling_rate'])*1000)/1000)
                LenTrace = subStream.stats.npts
                
                if LenTrace>BiggestLenTrace:
                    BiggestLenTrace = LenTrace
                    FrequenceLongestTrace = FrequenceTrace
                    IndexLongestTrace = indexTrace
        return FrequenceLongestTrace, IndexLongestTrace

    def __makeTreatmentPieceOfTrace(self, Trace):
        Trace -= numpy.mean(Trace)
        return scipy.signal.detrend(Trace)
        

    def makeArrayToTreatAndGiveStartTime(self, date):
        LastFileOpened = ''
        # print("                               Traces used:")
        starttime = datetime.strptime(date, "%Y/%j")
        endtime = starttime + timedelta(seconds=int(self.LenTrace/self.NewFrequence))
        for infile, indexTrace, channel in self.ListFileStationCompoOneDayWithIndex:
            if channel[:2] == self.BestCode:
                # print("                                  -> {} {}".format(channel, infile))
                if not LastFileOpened == infile:
                    try:
                        Stream = obspy.core.read(infile)
                    except:
                        # print('Can\'t open the file :' + infile)
                        sys.exit()#The file have been already opened. It should work.
                LastFileOpened = infile
                
                subStream = Stream[indexTrace]
                subStream.trim(obspy.core.UTCDateTime(starttime), obspy.core.UTCDateTime(endtime))
                
                StationTrace = str(subStream.stats['station'])
                ComponentTrace = str(subStream.stats['channel'])
                FrequenceTrace = float(numpy.round(float(subStream.stats['sampling_rate'])*1000)/1000)
                PeriodTrace = 1.0/FrequenceTrace
                StartDateTimeTrace = subStream.stats['starttime'].datetime #Convert in datetime object
                Trace = subStream.__dict__['data']
                self.StationFullName = "{}.{}.{}.{}".format(subStream.stats.network,
                                                            subStream.stats.station,
                                                            subStream.stats.location,
                                                            subStream.stats.channel)
                #Trace = self.__makeTreatmentPieceOfTrace(Trace)
                #If trace have problem (check with the function checkTraceInfo), we put it aside
                if self.__checkTraceInfo(infile, Trace, indexTrace, StationTrace, ComponentTrace, FrequenceTrace):
                    IndexBeginTrace = self.__giveIndexBeginTrace(PeriodTrace, StartDateTimeTrace)
                    if IndexBeginTrace+len(Trace)>self.DurationTraceSave:
                        self.TraceToTreated[IndexBeginTrace:] = Trace[:self.DurationTraceSave-IndexBeginTrace]
                    else:
                        self.TraceToTreated[IndexBeginTrace: IndexBeginTrace + len(Trace)] = Trace
        sys.stdout.flush()
        sys.stderr.flush()
        return StartDateTimeTrace
    
    def __checkTraceInfo(self, Infile, Trace, IndexTrace, StationTrace, ComponentTrace, FrequenceTrace):
        #If the trace has problem, booleen value TraceIsGood is False, it should not take into account.
        #if not StationTrace == self.station:
         #   print 'Name architecture station' + self.station,
          #  print ' is different than trace station' +  StationTrace + ' in file:' + Infile
            #TraceIsGood = False
    
        #if not ComponentTrace == self.ComponentStation:
         #   print 'Name architecture component' + self.ComponentStation,
          #  print ' is different than trace component' +  ComponentTrace + ' in file:' + Infile
            #TraceIsGood = False
            
        if len(Trace) == 0:
            return False
    
        if not FrequenceTrace == self.Frequency:
            add_log(f"The Frequency of the first trace in stream ({self.Frequency} Hz) is different than the frequency in current trace ({FrequenceTrace} Hz) with index {IndexTrace} in file {Infile}", level="error")
            return False
    
        if numpy.max(numpy.isnan(Trace)):
            add_log(f"The trace in stream (index: {IndexTrace}) contains only NaN values in file {Infile}", level="warning")
            return False
        
        return True
    
    def __giveIndexBeginTrace(self, Period, StartTime):
        TimeSecBegin = 3600*StartTime.hour+60*StartTime.minute+StartTime.second+1.e-6*StartTime.microsecond
        IndexBeginTrace = int(TimeSecBegin/float(Period))
        if 2*(TimeSecBegin%Period) >=  Period:
            IndexBeginTrace += 1
        return  IndexBeginTrace

    def timeCorrectionTrace(self, station, date, ErrorStartTime=5.e-6):
        #Trace is destroyed
        #__StartDateTimeTrace is a datetime object
        #ErrorStartTime is expressed in second
        try:
            Period = 1.0/float(self.Frequency)
            TimeSecBegin = 3600*self.__StartDateTimeTrace.hour+60*self.__StartDateTimeTrace.minute+self.__StartDateTimeTrace.second+1.e-6*self.__StartDateTimeTrace.microsecond
            DiffStartTimeAndSampling = TimeSecBegin%Period
            if 2*DiffStartTimeAndSampling >=  Period:
                DiffStartTimeAndSampling -= Period
            if abs(DiffStartTimeAndSampling) >= ErrorStartTime:
                L = len(self.TraceToTreated)
                tr = numpy.zeros(L, dtype = 'complex')
                tr[0:int(L/2)-1] = scipy.fftpack.fft(self.TraceToTreated, overwrite_x=True)[0:int(L/2)-1]
                tr[0:int(L/2)-1] *= numpy.exp(-1j*2*numpy.pi*numpy.arange(int(L/2)-1)/Period/(L)*DiffStartTimeAndSampling)
                return 2.0*numpy.real(scipy.fftpack.ifft(tr))
            else:
                return self.TraceToTreated
        except:
            add_log(f"Time correction for station {station} and day {date} failed. Skipping correction.", level="warning")
            return self.TraceToTreated
        
if __name__ == '__main__':
    pass
