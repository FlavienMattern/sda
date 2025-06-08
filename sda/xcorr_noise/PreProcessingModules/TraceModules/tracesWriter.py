################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Classes and methods to save the traces.

Module tracesWriter
===================

.. inheritance-diagram::
         WriterTraces
         WriterOneTraceNpy
         WriterOneTraceMat
        :parts: 1
"""

import os
from sda.xcorr_noise.PreProcessingModules.TraceModules import tracesExceptions
import numpy
import scipy.io

class WriterTraces(object):
    """
    Provide a method :func:`getNameDirAndFileSave` to get the path directory and the file name 
    for save the traces.
    
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatTraceSave*, *SaveDirectory*, *ComponentStation*.
    
    """
    def __init__(self, param):
        try:
            self.FormatTraceSave = param.FormatTraceSave
            self.SaveDirectory = param.SaveDirectory
            self.ComponentStation = param.ComponentStation
        except AttributeError:
            raise tracesExceptions.ErrorParamAttribute(classBadAttribute='WriterTraces', ListMissingAttribute=['FormatTraceSave', 'SaveDirectory', 'ComponentStation'])
        self.SeparatorDirComponent = '_TRACE'
        
    def getNameDirAndFileSave(self, Date, Station):
        """
        Return a path directory dependent of the date and a file name dependent of the station.  
        """
        DirPathSave = self.SaveDirectory + os.sep + self.ComponentStation + self.SeparatorDirComponent + os.sep + Date + os.sep
        FileSave = Station + '.' + self.FormatTraceSave
        #FileSave = FileSave = station[0:3]+station[4:-1] 
        return DirPathSave, FileSave
    
    def tryMakeDirectories(self, DirSave):
        """
        Write all the directories defined in the path directory
        with right 770 if they do not exist.
        
        :Parameter:
            
            **DirSave**: str
                The path directory.
                
        .. Note::
            If it is not possible, catch the exception and print a message. 
            (Try twice for concurrency problems.)
        """
        if not os.path.isdir(DirSave):
            try: 
                os.makedirs(DirSave, 0o770)
            except:
                try:
                    os.makedirs(DirSave, 0o770)
                except:
                    pass
        
    def writeOneTrace(self):
        """
        Abstract method, not implemented.
        """
        raise NotImplementedError#Abstract method

    def printFileSave(self, DirSave, FileSave):
        # print('[INFO] Save PreProcessing : ' + DirSave + FileSave)
        pass
        
class WriterOneTraceNpy(WriterTraces):
    """
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatTraceSave*, *SaveDirectory*, *ComponentStation*.
    """
            
    def writeOneTrace(self, DirSave, FileSave, Trace):
        """
        Save a trace with the file path given and the format numpy (.npy).
        
        :Parameters:
        
            **Trace**: numpy array
                The trace to be saved.
        
            **DirSave**: str
                Directory name to save the trace.
                
            **FileSave**: str
                File name of the trace saved.
        
        (Try twice to save the trace for concurrency problems.)
        """
        self.tryMakeDirectories(DirSave)
        try:
            numpy.save(DirSave + FileSave, Trace)
            self.printFileSave(DirSave, FileSave)
        except:
            try:
                print(('try second time to save the trace in: ' + DirSave + FileSave))
                numpy.save(DirSave + FileSave, Trace)
                self.printFileSave(DirSave, FileSave)
            except:
                print(('cannot save the trace:' + DirSave + FileSave))
    
class WriterOneTraceMat(WriterTraces):
    """
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatTraceSave*, *SaveDirectory*, *ComponentStation*.
    """
    def writeOneTrace(self, DirSave, FileSave, Trace):
        """
        Save a trace with the file path given and the format matlab (.mat).
        
        :Parameters:
            
            **Trace**: numpy array
                The trace to be saved.
        
            **DirSave**: str
                Directory name to save the trace.
                
            **FileSave**: str
                File name of the trace saved.
        
        (Try twice to save the trace for concurrency problems.)
        
        .. Note:: 
            The field in the matlab structure for the array of the trace is **'trace'**.
        """
        self.tryMakeDirectories(DirSave)
        try:
            scipy.io.savemat(DirSave + FileSave, {'trace':Trace})
            self.printFileSave(DirSave, FileSave)
        except:
            try:
                print(('try second time to save the trace in: ' + DirSave + FileSave))
                scipy.io.savemat(DirSave + FileSave, {'trace':Trace})
            except:
                print(('cannot save the trace:' + DirSave + FileSave))
                self.printFileSave(DirSave, FileSave)

if __name__ == '__main__':
    pass      
