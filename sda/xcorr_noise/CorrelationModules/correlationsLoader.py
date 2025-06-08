################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Classes and methods to load the traces.

Module correlationsLoader
=========================

.. inheritance-diagram::
         LoaderTrace
         LoaderOneTraceNpy
         LoaderOneTraceMat
         :parts: 1

"""

# import correlationsExceptions
from sda.xcorr_noise.CorrelationModules import correlationsExceptions
import numpy
import os
import scipy.io

class LoaderTrace(object):
    """
    Provide a method :func:`getDirAndFileLoadTrace` to get the path directory and the file name 
    for loading the traces.
    
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatTrace*, *LoadDirectory*.
    
    """
    def __init__(self, param, acorr):
        try:
            self.PathRootTrace = param.LoadDirectory + os.sep
            self.FormatTrace = param.FormatTrace
            self.acorr = acorr
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='LoaderTrace', ListMissingAttribute=['LoadDirectory','FormatTrace'])
    
    def getDirAndFileLoadTrace(self, Component, Date, Station, path_acorr):
        """
        Return a path directory dependent of the component and the date and a file name dependent of the station.  
        """
        if path_acorr == True:
            DirTraceCompo = Component + '_TRACE_ACORR'
        else:
            DirTraceCompo = Component + '_TRACE'
        DirTrace = self.PathRootTrace + os.sep + DirTraceCompo + os.sep + Date + os.sep
        #DirTraceCompo = Component + Component + '_TRACE'
        #DirTrace = self.PathRootTrace + os.sep + Date + os.sep + DirTraceCompo + os.sep
        FileTrace = Station + '.' + self.FormatTrace
        return DirTrace, FileTrace
    
    def loadOneTrace(self, DirTrace, FileTrace):
        """
        Abstract method, not implemented.
        """
        raise NotImplementedError#Abstract method

class LoaderOneTraceNpy(LoaderTrace):
    """
    Class to load traces with numpy format.
    
    
    :Base class: :class:`LoaderTrace`
        Inherits all attibutes of the base class.
        
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatTrace*, *LoadDirectory*.
            
    """
    def loadOneTrace(self, DirTrace, FileTrace):
        """
        Load a trace with the file path given and the format numpy (.npy).
        
        :Parameters:
        
            **DirSave**: str
                Directory name to load the trace.
                
            **FileSave**: str
                File name of the trace loaded.
        """
        return numpy.load(DirTrace + FileTrace)
    
class LoaderOneTraceMat(LoaderTrace):
    """
    Class to load traces with matlab format.
    
    :Base class: :class:`LoaderTrace`
        Inherits all attibutes of the base class.
        
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatTrace*, *LoadDirectory*.
            
    """
    def loadOneTrace(self, DirTrace, FileTrace):
        """
        Load a trace with the file path given and the format matlab (.mat).
        
        :Parameters:
        
            **DirSave**: str
                Directory name to load the trace.
                
            **FileSave**: str
                File name of the trace loaded.
        
        .. Note:: 
            Requirement: The field in the matlab structure for the array of the trace is **'trace'**.
        """
        return scipy.io.loadmat(DirTrace + FileTrace)['trace'][:,0]

if __name__ == '__main__':
    pass      
