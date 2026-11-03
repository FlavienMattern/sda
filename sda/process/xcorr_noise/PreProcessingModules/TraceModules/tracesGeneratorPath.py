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
from sda.process.xcorr_noise.PreProcessingModules.TraceModules import tracesExceptions
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
            self.WindowStart = obspy.core.UTCDateTime(ns=kwargs['config']["window_start_ns"], precision=9)
            self.WindowEnd = obspy.core.UTCDateTime(ns=kwargs['config']["window_end_ns"], precision=9)
            self.WindowKey = kwargs['config']["window_key"]
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
        traces = {}
        seen = {}
        for date, FilePickle in genDatePathFileDictOfTraces:
            with open(FilePickle, 'rb') as fileDictTraces:
                DictOfTracesOneDay = pickle.load(fileDictTraces)
                DictOfTracesOneDayOneCompo = self.__fromDictTraceStationToDictTracesStationOneCompo(DictOfTracesOneDay, self.ComponentStation)
                for station, infos in DictOfTracesOneDayOneCompo.items():
                    traces.setdefault(station, [])
                    seen.setdefault(station, set())
                    for info in infos:
                        if (obspy.core.UTCDateTime(info['endtime']).ns < self.WindowStart.ns
                                or obspy.core.UTCDateTime(info['starttime']).ns >= self.WindowEnd.ns):
                            continue
                        key = (info['nameFile'], info['channel'], info['ntrace'])
                        if key not in seen[station]:
                            seen[station].add(key)
                            traces[station].append(info)
        yield (self.WindowKey, traces)

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


class generatorArrayBeTreatFrequenceAndPathSave(generatorPathSaveStationListFilesStationOneDay):
    """
    **A generator**
    
    Generate, for each date and each station:
    
        * the date
        * the trace to treated
        * the frequency of the sampling
        * the path file to save the treatment
    
    :Base class: :class:`generatorPathSaveStationListFilesStationOneDay`
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
    
    def __iter__(self):
        genDateDictOfTracesOneComponent = generatorPathSaveStationListFilesStationOneDay.__iter__(self)
        for date, station, DirPathSave, FileSave, ListFileStationCompoOneDayWithIndex in genDateDictOfTracesOneComponent:
            self.station = station
            self.ListFileStationCompoOneDayWithIndex = ListFileStationCompoOneDayWithIndex
            self.BestCode = self.selectBestChannelCode()

            self.Frequency, IndexLongestTrace = self.giveFrequenceAndIndexFromTheLongestTrace(date)
            if self.Frequency == 0:
                yield (date, numpy.array([]), 0, DirPathSave, FileSave, station)
                continue
            self.DurationTraceSave = int(round(float(self.Frequency) * (self.WindowEnd - self.WindowStart)))
            self.TraceToTreated = numpy.zeros(self.DurationTraceSave, dtype='float')
            self.StationFullName = ""
            try:
                self.__StartDateTimeTrace = self.makeArrayToTreatAndGiveStartTime(date)
            except Exception:
                yield (date, numpy.array([]), self.Frequency, DirPathSave, FileSave, station)
                continue
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


    def npts_in_window(self, tr, starttime, endtime):
        fs = float(tr.stats.sampling_rate)
        trace_start = tr.stats.starttime
        trace_end = tr.stats.endtime

        overlap_start = max(trace_start, starttime)
        overlap_end = min(trace_end, endtime)

        if overlap_end < overlap_start:
            return 0

        return int(round((overlap_end - overlap_start) * fs)) + 1

        
    def giveFrequenceAndIndexFromTheLongestTrace(self, date):
        
        starttime = self.WindowStart
        endtime = self.WindowEnd
        
        FrequenceLongestTrace = 0.0
        BiggestLenTrace = 0.0
        IndexLongestTrace = 0
        LastFileOpened = ''
        self.files_ignore = []
        for infile, indexTrace, channel in self.ListFileStationCompoOneDayWithIndex:

            if channel[:2] == self.BestCode:
                if not LastFileOpened == infile:
                    try:
                        Stream = obspy.core.read(infile, headonly=True)      
                    except Exception as err:
                        msg = f"An error occurred while read header file '{infile}'. Skipping file.\n"
                        msg += "Error details:\n"
                        msg += traceback.format_exc()
                        add_log(msg, level="error")
                        self.files_ignore.append(infile)
                        continue
                    LastFileOpened = infile
                
                subStream = Stream[indexTrace]
                # subStream.trim(obspy.core.UTCDateTime(starttime), obspy.core.UTCDateTime(endtime))
                # FrequenceTrace = float(numpy.round(float(subStream.stats['sampling_rate'])*1000)/1000)
                # LenTrace = subStream.stats.npts
                FrequenceTrace = float(numpy.round(float(subStream.stats.sampling_rate) * 1000) / 1000)
                LenTrace = self.npts_in_window(subStream, starttime, endtime - 1.0 / FrequenceTrace)

                if LenTrace>BiggestLenTrace:
                    BiggestLenTrace = LenTrace
                    FrequenceLongestTrace = FrequenceTrace
                    IndexLongestTrace = indexTrace

        return FrequenceLongestTrace, IndexLongestTrace


    def makeArrayToTreatAndGiveStartTime(self, date):
        LastFileOpened = ''
        starttime = self.WindowStart
        endtime = self.WindowEnd
        StartDateTimeTrace = None
        for infile, indexTrace, channel in self.ListFileStationCompoOneDayWithIndex:

            if infile in self.files_ignore: continue

            if channel[:2] == self.BestCode:
                if not LastFileOpened == infile:
                    try:
                        Stream = obspy.core.read(infile)
                    except Exception as err:
                        msg = f"An error occurred while read file '{infile}'. Filling trace with zeros.\n"
                        msg += "Error details:\n"
                        msg += traceback.format_exc()
                        add_log(msg, level="error")
                        self.files_ignore.append(infile)
                        continue
                    LastFileOpened = infile
                
                
                subStream = Stream[indexTrace].copy()
                subStream.trim(starttime, endtime - subStream.stats.delta)
                if not subStream.stats.npts:
                    continue
                
                StationTrace = str(subStream.stats['station'])
                ComponentTrace = str(subStream.stats['channel'])
                FrequenceTrace = float(numpy.round(float(subStream.stats['sampling_rate'])*1000)/1000)
                StartDateTimeTrace = subStream.stats['starttime'].datetime #Convert in datetime object
                Trace = subStream.__dict__['data']
                self.StationFullName = "{}.{}.{}.{}".format(subStream.stats.network,
                                                            subStream.stats.station,
                                                            subStream.stats.location,
                                                            subStream.stats.channel)

                IndexBeginTrace = int(round((subStream.stats.starttime - starttime) * self.Frequency))
                #If trace have problem (check with the function checkTraceInfo), we put it aside
                if self.__checkTraceInfo(infile, Trace, indexTrace, StationTrace, ComponentTrace, FrequenceTrace):
                    if IndexBeginTrace < 0:
                        Trace = Trace[-IndexBeginTrace:]
                        IndexBeginTrace = 0
                    if IndexBeginTrace >= self.DurationTraceSave:
                        continue
                    if IndexBeginTrace+len(Trace)>self.DurationTraceSave:
                        self.TraceToTreated[IndexBeginTrace:] = Trace[:self.DurationTraceSave-IndexBeginTrace]
                    else:
                        self.TraceToTreated[IndexBeginTrace: IndexBeginTrace + len(Trace)] = Trace

        sys.stdout.flush()
        sys.stderr.flush()

        if StartDateTimeTrace is None:
            raise ValueError("No data overlap the requested interval.")
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
