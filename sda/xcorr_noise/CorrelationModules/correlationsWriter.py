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
# import correlationsExceptions
from sda.xcorr_noise.CorrelationModules import correlationsExceptions
import os
import scipy.io
import numpy

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
            self.DirCorrComponent = param.ComponentFirstStation + param.ComponentSecondStation + '_CORRC1' 
            self.DirSaveCompo = self.SaveDirectory + os.sep + self.DirCorrComponent
        except AttributeError:
            raise correlationsExceptions.ErrorParamAttribute(classBadAttribute='WriterCorrelation', ListMissingAttribute=['SaveDirectory', 'ComponentFirstStation', 'ComponentSecondStation'])
        self.SeparatorDirStation = '_CORRC1'
        self.SeparatorCoupleStations = '_CORRC1_'
        
    def getDirAndFileSaveCorrelation(self, Date, FirstStation, SecondStation):
        """
        Return a path directory dependent of the date and a file name dependent of the a couple of stations.  
        """
        DirSave = self.DirSaveCompo + os.sep + Date + os.sep + FirstStation + self.SeparatorDirStation + os.sep
        FileSave = FirstStation + self.SeparatorCoupleStations + SecondStation + '.' + self.FormatSave
        return DirSave, FileSave
    
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
        
    def writeOneCorrelation(self):
        """
        Abstract method, not implemented.
        """
        raise NotImplementedError#Abstract method

class WriterOneCorrelationNpy(WriterCorrelation):
    """
    :Base class: :class:`WriterCorrelation`
        Inherits all attibutes of the base class.
        
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatSave*, *SaveDirectory*, *ComponentFirstStation*, *ComponentSecondStation*.
            
    """
    def writeOneCorrelation(self, DirSave, FileSave, corr):
        """
        Save a correlation with the file path given and the format numpy (.npy).
        
        :Parameters:
        
            **corr**: numpy array
                The correlation to be saved.
        
            **DirSave**: str
                Directory name to save the trace.
                
            **FileSave**: str
                File name of the trace saved.
        
        (Try twice to save the correlations for concurrency problems.)
        """
        self.tryMakeDirectories(DirSave)
        try:
            numpy.save(DirSave + FileSave, corr)
            # print("[INFO] Save Correlation : {}{}".format(DirSave, FileSave))
        except:
            try:
                print('try second time to save the correlation in: ' + DirSave + FileSave)
                numpy.save(DirSave + FileSave, corr)
            except:
                print('cannot save the correlation:' + DirSave + FileSave)
    
class WriterOneCorrelationMat(WriterCorrelation):
    """
    :Base class: :class:`WriterCorrelation`
        Inherits all attibutes of the base class.
    
    :Parameter:
    
        **param** : obj
        
            Object with attributes  *FormatSave*, *SaveDirectory*, *ComponentFirstStation*, *ComponentSecondStation*.
    """
    def writeOneCorrelation(self, DirSave, FileSave, corr):
        """
        Save a correlation with the file path given and the format matlab (.mat).
        
        :Parameters:
        
            **corr**: numpy array
                The correlation to be saved.
        
            **DirSave**: str
                Directory name to save the trace.
                
            **FileSave**: str
                File name of the trace saved.
        
        (Try twice to save the correlations for concurrency problems.)
        """
        self.tryMakeDirectories(DirSave)
        try:
            scipy.io.savemat(os.path.join(DirSave, FileSave), {'corr':corr})
            # print("[INFO] Save Correlation : {}{}".format(DirSave, FileSave))
        except:
            try:
                print('try second time to save the correlation in: ' + DirSave + FileSave)
                scipy.io.savemat(os.path.join(DirSave, FileSave), {'corr':corr})
            except:
                print('cannot save the correlation:' + DirSave + FileSave)

if __name__ == '__main__':
    pass      


