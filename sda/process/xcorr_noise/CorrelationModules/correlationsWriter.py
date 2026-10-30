################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Classes and methods to save the traces.

Module correlationsWriter
=========================

"""

from sda.process.xcorr_noise.CorrelationModules import correlationsExceptions
from datetime import datetime
import os


class WriterCorrelation(object):
    """
    Provide a method :func:`getDirAndFileSaveCorrelation` to get the path directory and the file name 
    for saving the correlation.
    
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatSave*, *SaveDirectory*, *ComponentFirstStation*, *ComponentSecondStation*.
    
    """
    
    def __init__(self, param):
        try:
            self.FormatSave = param.FormatSave
            self.SaveDirectory = param.SaveDirectory
            self.DirCorrComponent = param.ComponentFirstStation + param.ComponentSecondStation
            self.DirSaveCompo = os.path.join(self.SaveDirectory, self.DirCorrComponent)
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='WriterCorrelation', ListMissingAttribute=['SaveDirectory', 'ComponentFirstStation', 'ComponentSecondStation'])

        
    def getDirAndFileSaveCorrelation(self, Date, FirstStation, SecondStation):
        """
        Return a path directory dependent of the date and a file name dependent of the a couple of stations.  
        """
        DirSave = os.path.join(self.DirSaveCompo, f"{FirstStation}-{SecondStation}")
        day_str = os.path.basename(Date) if Date.startswith("windows" + os.sep) else datetime.strptime(Date, "%Y/%j").strftime("%Y-%m-%d")
        FileSave = os.path.join(DirSave, f"{day_str}.mat")
        return DirSave, FileSave


if __name__ == '__main__':
    pass      


