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

.. inheritance-diagram::
         WriterCorrelation
         WriterOneCorrelationNpy
         WriterOneCorrelationMat
         :parts: 1

"""

from sda.process.xcorr_noise.CorrelationModules import correlationsExceptions
from datetime import datetime
import os
import scipy.io
from sda.core.logs import add_log
import traceback



class WriterCorrelation(object):
    """
    Provide a method :func:`getDirAndFileSaveCorrelation` to get the path directory and the file name 
    for save the correlation and a method :func:`tryMakeDirectories` in order to create a path directory.
    
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
        day_str = datetime.strptime(Date, "%Y/%j").strftime("%Y-%m-%d")
        FileSave = os.path.join(DirSave, f"{day_str}.mat")
        return DirSave, FileSave
    
        
    
class WriterOneCorrelation(WriterCorrelation):

    def save_xcorr(self, DirSave, FileSave, corr, max_lag, fs):

        os.makedirs(DirSave, exist_ok=True)

        try:
            scipy.io.savemat(os.path.join(DirSave, FileSave),
                             {"corr":corr, "max_lag":max_lag,"fs": fs})

        except:
            msg = f"Cannot save correlation: {os.path.join(DirSave, FileSave)}\n"
            msg += traceback.format_exc()
            add_log(msg, level="error")

            

if __name__ == '__main__':
    pass      


