################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Make the dictionaries of traces before processing.

Module tracesDictOfTraces
=========================

.. topic:: traces.tracesDictOfTraces

    * Provide a class :class:`DictOfTraces` in order make the dictionaries of traces before treat them.
    
    * Dictionaries contains all the metadata of the traces whose corresponding files are contained\
     in a directory defined by the attribute **LoadDirectory** and these files are classical format\
     for seismogram: they are open by the obspy.core.read() function of the **obspy library**\
     (see http://docs.obspy.org/packages/autogen/obspy.core.stream.read.html).

    * Each dictionary, one for each date, contains all the necessary informations (metadata),\
     particularly for classify traces with their station and their starttime.
    
"""

import datetime
import sys
import os
import glob
import obspy.core
import numpy
import pickle
import operator
import sqlite3
from sda.process.xcorr_noise.PreProcessingModules.TraceModules import tracesExceptions
from sda.core.logs import add_log
from tqdm import tqdm
import traceback

import warnings
warnings.filterwarnings('ignore')


class DictOfTraces():
    """
    Provides methods in order to make dictionaries of all the "metadata" of traces contained in a directory.
    
    The methods permits to built a **dictionary** for **each date** of the form:
    
        {Station{Component{List of files with the indexes of traces and the metadata}}}.
    
    :Attributes:
        
        **SaveDirectory**: str
            Defined in the module :mod:`tracesParamIO`
        
        **LoadDirectory**: str
            Defined in the module :mod:`tracesParamIO`
        
        **ListOfStations**: list
            Defined in the module :mod:`tracesParamIO`
        
        **ListOfDates**: lis
            Defined in the module :mod:`tracesParamIO`
            
        **PrefixNameFileDictsOfTraces**: str
            Defined in the module :mod:`tracesParamIO`
        
        **PathDirDictsOfTraces**: str
            Defined in the module :mod:`tracesParamIO`
        
        **PathDirectoryTemp**: str
            The directory for saving temporary file.
            
        **NumberMaxTracesOneDictOfTraces**: int
            The maximum number of traces in one dictionary of traces.
    """
    def __init__(self, config, **kwargs):
        try:
            self.config = config
            self.SaveDirectory = kwargs['param'].SaveDirectory
            self.LoadDirectory = kwargs['param'].LoadDirectory
            self.ListOfStations = kwargs['param'].ListOfStations
            self.ListOfDates = kwargs['param'].ListOfDates
            self.PrefixNameFileDictsOfTraces = kwargs['param'].PrefixNameFileDictsOfTraces
            self.PathDirDictsOfTraces = kwargs['param'].PathDirDictsOfTraces
        except AttributeError:
            raise tracesExceptions.ErrorParamAttribute(classBadAttribute='DictOfTraces', ListMissingAttribute=['SaveDirectory', 'LoadDirectory', 'ListOfStations', 'ListOfDates', 'PrefixNameFileDictsOfTraces', 'PathDirDictsOfTraces'])
          
        try:
            self.getDirAndFileDictOfDoublet =  kwargs['param'].getDirAndFileDictOfDoublet
        except AttributeError:
            raise tracesExceptions.ErrorParamAttribute(classBadAttribute='DictOfTraces', ListMissingMethod=['getDirAndFileDictOfDoublet'])

        DateNow = datetime.datetime.strftime(datetime.datetime.now(),"%d-%m-%Y_%H-%M-%S-%U")
        self.PathDirectoryTemp = self.SaveDirectory + os.sep + "TEMP" + DateNow + os.sep
        self.__PrefixNameTempFile = "TempDictOfTraces"
        self.NumberMaxTracesOneDictOfTraces = 1000
    
    def __getNameTemporaryFile(self, numberOfFile):
        return self.PathDirectoryTemp + os.sep + self.__PrefixNameTempFile + str(numberOfFile)
    
    def __getPatternNameTemporaryFile(self):
        return self.PathDirectoryTemp + os.sep + self.__PrefixNameTempFile
    
    def writeDirectory(self, pathDir):
        """
        Write all the directories defined in the path directory with right 755 if they
        do not exist.
        
        :Parameter:
            
            **pathDir**: str
                The path directory.
                
        .. Note::
            If it is not possible, catch the exception and print a message. 
            (Try twice for concurrency problems.)
        """
        os.makedirs(pathDir, exist_ok=True)
    
    def removeTemporaryDirectory(self):
        """
        Remove temporary directory and all the temporary files (made in order to create the dictionaries of traces).
        If it is not possible, just print a message.
        """
        for file in glob.iglob(self.__getPatternNameTemporaryFile() + '*'):
            try:
                os.remove(file)
            except os.error:
                print(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), end=" ")
                print('[ERROR] Can\'t remove the file: ' + file)
        try:
            os.rmdir(self.PathDirectoryTemp)
        except os.error:
            print(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), end=" ")
            print('[ERROR] Can\'t remove the directory: ' + self.PathDirectoryTemp)

    def makeTempPickleFilesOfDictOfTraces(self):
        """
        Built temporary dictionaries of the form:
        
            {year{JulianDay{Station{Component{List of files with the indexes of traces and the metadata}}}}}.
        
        .. Note::
            Each dictionary contains at most **NumberMaxTracesOneDictOfTraces** traces.
        
        """
        DictOfTraces = {}
        NumberOfTraces = 0
        NumberOfTempPickleFileDictOfTraces = 0
        
        # Connecting to database
        conn = sqlite3.connect(self.config["databasePath"])
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM DATASET")
        colnames = [description[0] for description in cursor.description]
        
        for idx, row in enumerate(cursor.fetchall()):

            row_dict = dict(zip(colnames, row))
            DictInfosFile = {
                "nameFile": row_dict["FILE"],
                "ntrace": row_dict["NTRACE"],
                "channel": row_dict["CHANNEL"],
                "sampling_rate": row_dict["SAMPLING_RATE"],
                "delta": row_dict["DELTA"],
                "starttime": row_dict["STARTTIME"],
                "endtime": row_dict["ENDTIME"],
                "npts": row_dict["NPTS"],
                "calib": row_dict["CALIB"],
                "network": row_dict["NETWORK"],
                "location": row_dict["LOCATION"],
            }

            try:
                
                starttime = obspy.core.UTCDateTime(DictInfosFile["starttime"]).datetime
                endtime = obspy.core.UTCDateTime(DictInfosFile["endtime"]).datetime
                k = 1 if starttime.day==endtime.day else 2
                date_list = [starttime + datetime.timedelta(days=i) for i in range((endtime - starttime).days + k)]
                days = [(date.strftime("%j"), f"{date.year}") for date in date_list] 
                NameStation = row_dict["STATION"]
                Channel = row_dict["CHANNEL"]
                Component = Channel[-1]
                
                for JulianDay, Year in days:                    
                    if self.__isValidTrace(NameStation,  Year + os.sep + JulianDay):
                        NumberOfTraces += 1
                                
                        if Year not in DictOfTraces:
                            DictOfTraces[Year] = {JulianDay:{NameStation:{Component:[DictInfosFile]}}}
                        elif JulianDay not in DictOfTraces[Year]:
                            DictOfTraces[Year][JulianDay] = {NameStation:{Component:[DictInfosFile]}}
                        elif NameStation not in DictOfTraces[Year][JulianDay]:
                            DictOfTraces[Year][JulianDay][NameStation] = {Component:[DictInfosFile]}
                        elif Component not in DictOfTraces[Year][JulianDay][NameStation]:
                            DictOfTraces[Year][JulianDay][NameStation][Component] = [DictInfosFile]
                        else:
                            DictOfTraces[Year][JulianDay][NameStation][Component].append(DictInfosFile)
                
            except:
                msg = "An error occurred while collecting/formatting the following row from the database. Skipping row.\n"
                msg += f"Row {idx}:\n"
                for key in DictInfosFile:
                    msg += f"  - {key} : {DictInfosFile[key]}\n"
                msg += traceback.format_exc()
                add_log(msg, level="error")
                continue
            
            
            if NumberOfTraces > self.NumberMaxTracesOneDictOfTraces:
                NumberOfTraces = 0
                FilePickle = self.__getNameTemporaryFile(NumberOfTempPickleFileDictOfTraces)
                with open(FilePickle, 'wb') as fileDictTraces:
                    # print('save temporary file pickle DictOfTraces: ' + FilePickle)
                    pickle.dump(DictOfTraces, fileDictTraces, -1)
                    NumberOfTempPickleFileDictOfTraces += 1
                DictOfTraces = {}
                
        # Save the last dictionary of traces
        FilePickle = self.__getNameTemporaryFile(NumberOfTempPickleFileDictOfTraces)
        with open(FilePickle, 'wb') as fileDictTraces:
            # print('Save temporary file pickle DictOfTraces: ' + FilePickle)
            pickle.dump(DictOfTraces, fileDictTraces, -1)
            NumberOfTempPickleFileDictOfTraces += 1   
            
            
        
        ################################################################################################
        # # Counting number of files
        # count = 0
        # for dirpath, dirnames, filenames in os.walk(self.LoadDirectory):
        #     #print(dirpath)
        #     for k, file in enumerate(filenames):
        #         count += 1
        # # Scanning files
        # with tqdm(total=count, bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
        #     pbar.set_description(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Scan            ")
        #     idx = 1
        #     for dirpath, dirnames, filenames in os.walk(self.LoadDirectory):
        #         for k, file in enumerate(filenames):  # Au lieu d'énumérer sur les fichiers, énumérer sur les base de données !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #             pbar.update()
        #             try:
        #                 StreamOfTrace = obspy.core.read(dirpath + os.sep + file, headonly=True)
        #                 for indexOfTrace, trace in enumerate(StreamOfTrace.traces):
        #                     #NameStation = trace.stats['station']
        #                     NameStation = "".join(trace.stats['station'].split('\x00'))
        #                     Channel = trace.stats['channel']
        #                     Component = Channel[2]#Component = Channel[-1]
        #                     FreqSamplingRate = float(numpy.round(float(trace.stats['sampling_rate'])*1000)/1000)
        #                     DateTime = trace.stats['starttime']
        #                     Year = str(DateTime.year)#A string
        #                     JulianDay = self.giveJulianDayTraceFromDateTime(DateTime, FreqSamplingRate)#A string as '042'
        #                     if self.__isValidTrace(NameStation,  Year + os.sep + JulianDay):
        #                         NumberOfTraces += 1
        #                         DictInfosFile = {'nameFile': dirpath + os.sep + file, 'indexTrace': indexOfTrace, 'channel': Channel}
        #                         for key, value in list(trace.stats.items()):
        #                             if (not key == 'channel') and (not  key == 'station'):
        #                                 DictInfosFile[key] = value
                                        
        #                         if Year not in DictOfTraces:
        #                             DictOfTraces[Year] = {JulianDay:{NameStation:{Component:[DictInfosFile]}}}
        #                         elif JulianDay not in DictOfTraces[Year]:
        #                             DictOfTraces[Year][JulianDay] = {NameStation:{Component:[DictInfosFile]}}
        #                         elif NameStation not in DictOfTraces[Year][JulianDay]:
        #                             DictOfTraces[Year][JulianDay][NameStation] = {Component:[DictInfosFile]}
        #                         elif Component not in DictOfTraces[Year][JulianDay][NameStation]:
        #                             DictOfTraces[Year][JulianDay][NameStation][Component] = [DictInfosFile]
        #                         else:
        #                             DictOfTraces[Year][JulianDay][NameStation][Component].append(DictInfosFile)

        #                 idx += 1
        #             except AttributeError:
        #                 idx += 1
        #                 continue
        #             except:

        #                 idx += 1
        #                 continue
                    
        #             if NumberOfTraces > self.NumberMaxTracesOneDictOfTraces:
        #                 NumberOfTraces = 0
        #                 FilePickle = self.__getNameTemporaryFile(NumberOfTempPickleFileDictOfTraces)
        #                 with open(FilePickle, 'wb') as fileDictTraces:
        #                     # print('save temporary file pickle DictOfTraces: ' + FilePickle)
        #                     pickle.dump(DictOfTraces, fileDictTraces, -1)
        #                     NumberOfTempPickleFileDictOfTraces += 1
        #                 DictOfTraces = {}#clean the dictionary

        # #Save the last dictionary of traces
        # FilePickle = self.__getNameTemporaryFile(NumberOfTempPickleFileDictOfTraces)
        # with open(FilePickle, 'wb') as fileDictTraces:
        #     # print('Save temporary file pickle DictOfTraces: ' + FilePickle)
        #     pickle.dump(DictOfTraces, fileDictTraces, -1)
        #     NumberOfTempPickleFileDictOfTraces += 1      
    ################################################################################################

    def __isValidTrace(self, NameStation, Date):
        ValidTrace = True
        # Les lignes commentées en dessous permettent de totu inclure dans le scan des données
        # if NameStation not in self.ListOfStations:
        #     ValidTrace = False
        # elif Date not in self.ListOfDates:
        #     ValidTrace = False
        return ValidTrace
      
    def giveJulianDayTraceFromDateTime(self, DateTime, FreqSamplingRate):
        """
        Return a string of 3 characters 'ccc' that correspond to the julian day, e.g. '024', of the second sampling
        induced by the date and the frequency of the sampling.
        
        :Parameter:
            
            **DateTime**: datetime.datetime object or obspy.core.utcdatetime.UTCDateTime object
                DateTime is a date. 
                
            **FreqSamplingRate**: float
                The frequency sampling in Hz. FreqSamplingRate must be greater than 1.0.
        
        .. Note::
        
            For  UTCDateTime object, see:
            http://docs.obspy.org/packages/autogen/obspy.core.utcdatetime.UTCDateTime.html
        
        :Example:
          
            >>> x=datetime.datetime(2007, 12, 6, 23, 59, 59, 995000)
            >>> print giveJulianDayTraceFromDateTime(x, 90)
            341
            >>> x=datetime.datetime(2007, 12, 6, 23, 59, 59, 985000)
            >>> print giveJulianDayTraceFromDateTime(x, 90)
            340
        
        """
        DeltaTimeOneSamplingRate = datetime.timedelta(microseconds=1e6/FreqSamplingRate)#We suppose frequence SamplingRate>1.0
        try:
            BeginTime = DateTime.datetime#We suppose that DateTime has attribute 'datetime' to be convert in datetime object
        except:
            BeginTime = DateTime

        FreqSamplingRate = float(numpy.round(float(FreqSamplingRate*1000)/1000))
        DateTimeTest = BeginTime + DeltaTimeOneSamplingRate
        JulianDay = int((DateTimeTest-datetime.datetime(DateTimeTest.year, 1, 1)).days + 1)
        if JulianDay <10:
            JulianDay = '00' + str(JulianDay)
        elif JulianDay <100:
            JulianDay = '0' + str(JulianDay)
        return str(JulianDay)
    
    
    def makeDictOfTraceOfOneDayFromTempFilesDictOfTraces(self):
        """
        For each date, built dictionaries of the form:
        
            {Station{Component{List of files with the indexes of traces and the metadata}}}.
        
        The directory where dictinorary are serialize (with cPickle) is defined by the method 
        getDirAndFileDictOfDoublet in the module :mod:`traces.tracesGetParam`.
        """
        # print(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), end=" ")
        # print('[INFO] Saving information in Daily files.')

        with tqdm(total=len(self.ListOfDates), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + " Scan Formatting ")
            for iday, date in enumerate(self.ListOfDates):
                pbar.update()
                year = date.split(os.sep)[0]
                day = date.split(os.sep)[1]
                DictOfTracesOneYearOneDay = {}#Dictionary is of the form {Station{Component{List of informations of files}}} (for each year, each day)
                FilePickle = self.getDirAndFileDictOfDoublet(day, year)
                if not os.path.isfile(FilePickle):
                    for tempFilePickle in glob.iglob(self.__getPatternNameTemporaryFile() + '*'): 
                        with open(tempFilePickle, 'rb') as fileDictTraces:
                            TempDictOfTraces = pickle.load(fileDictTraces)
                            if year in TempDictOfTraces:
                                if day in TempDictOfTraces[year]:
                                    for station in TempDictOfTraces[year][day]:
                                        for compo in TempDictOfTraces[year][day][station]:
                                            for dictInfosFile in TempDictOfTraces[year][day][station][compo]:
                                                if station not in DictOfTracesOneYearOneDay:
                                                    DictOfTracesOneYearOneDay[station] = {compo:[dictInfosFile]}
                                                else:
                                                    if compo not in DictOfTracesOneYearOneDay[station]:
                                                        DictOfTracesOneYearOneDay[station][compo] = [dictInfosFile]
                                                    else:
                                                        DictOfTracesOneYearOneDay[station][compo].append(dictInfosFile)
    
                if DictOfTracesOneYearOneDay:
                    for station in list(DictOfTracesOneYearOneDay.keys()):
                        for channel in DictOfTracesOneYearOneDay[station]:
                            DictOfTracesOneYearOneDay[station][channel].sort(key=operator.itemgetter('starttime'))
                    with open(FilePickle, 'wb') as fileDictTraces:
                        sys.stdout.flush()
                        pickle.dump(DictOfTracesOneYearOneDay, fileDictTraces, -1)
                    add_log(f"Saving metdata for day {iday+1}/{len(self.ListOfDates)}: DictOfTracesOneDay_{year}_{day}", level="info")

                        

    
if __name__ == '__main__':
    pass
    """
    param = tracesParamIO.Param()
    print param
    #del param.LoadDirectory
    t=DictOfTraces(param)
    #print t.__dict__
    """
