################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
General methods for the processing.

Module tracesTreatment
======================

"""
import sys
import numpy
import scipy.signal
import scipy.interpolate
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesDefineTreatments

class TreatmentTrace():
    """
    Provide general methods in order to control the workflow: methods to treat the
    traces before and after resampling and the resampling itself. 
    
    .. Note::
    
        Precise workflow is defined in the module :mod:`traces.TraceModules.tracesDefineTreatments`.
    """
    def __init__(self, **kwargs):
        self.NewFrequence = kwargs['param'].NewFrequence
    
    def makeTreatment(self, Trace, Frequence, acorr, remove_response, response_dict, config):
        """
        Return the trace treated with the following processing:
        
            1. Treat trace before resampling with the method :func:`makeTreatmentTraceBeforeNewFrequence`.
            
            2. Resampling with the method 'makeNewFrequenceTrace'.
            
            3. Treat trace after resampling with the method :func:`makeTreatmentTraceAfterNewFrequence`.
            
        """
        Trace = self.makeTreatmentTraceBeforeNewFrequence(Trace, Frequence, remove_response, response_dict, config)
        
        Trace = self.makeNewFrequenceTrace(Trace, Frequence, self.NewFrequence)

        TraceW, TraceNoW = self.makeTreatmentTraceAfterNewFrequence(Trace, self.NewFrequence, acorr, remove_response, response_dict, config)

        sys.stdout.flush()
        sys.stderr.flush()

        return TraceW, TraceNoW


    def makeNewFrequenceTrace(self, Trace, FrequenceTrace, NewFrequence):#destroy the trace, 
        """
        Return the trace resampled.

        .. Note::
        
            The ratio FrequenceTrace/NewFrequence must be either a float or a product 
            of powers of numeral in {2, 3, 4, 5, 6, 7, 8}.
            
                    
        """
        if float(NewFrequence) == float(FrequenceTrace):
            return Trace # We don't apply resampling if the target 
        if NewFrequence is not None:
            rateFreq = float(FrequenceTrace)/float(NewFrequence)
            if numpy.round(rateFreq, 3) == numpy.round(rateFreq, 0):#decimate does not work if rateFreq is not a multiple of {2,3,...,8}
                while rateFreq > 8:
                    ListDivisor = [8,7,6,5,4,3,2]
                    for divisor in ListDivisor:
                        if numpy.round(rateFreq/float(divisor), 3) == numpy.round(rateFreq/float(divisor), 0):
                            Trace = self.__makeDecimate(Trace, int(FrequenceTrace), int(FrequenceTrace/float(divisor)))
                            FrequenceTrace /= float(divisor)
                            rateFreq = float(FrequenceTrace)/float(NewFrequence)
                            break#in order to choice the bigger divisor
                Trace = self.__makeDecimate(Trace, int(FrequenceTrace), int(NewFrequence))
            else:
                Trace = self.__makeInterpolationNumpy(Trace, FrequenceTrace, NewFrequence)
        return Trace

    def __makeDecimate(self, Trace, Frequence, NewFrequence):
        return scipy.signal.decimate(Trace, int(float(Frequence)/float(NewFrequence)))

    def __makeInterpolationNumpy(self, Trace, Frequence, NewFrequence):
        VectorPeriodTrace = numpy.arange(0,len(Trace)/float(Frequence),1.0/float(Frequence))
        newVectorPeriodTrace = numpy.arange(0,int(len(Trace)/Frequence),1.0/NewFrequence)
        return numpy.interp(newVectorPeriodTrace,VectorPeriodTrace,Trace)
    
    def __makeInterpolationScipy(self, Trace, Frequence, NewFrequence):#Problem of memory leak, even with garbage collector gc: don't use now
        VectorPeriodTrace = numpy.arange(0,len(Trace)/float(Frequence),1.0/float(Frequence))
        newVectorPeriodTrace = numpy.arange(0,int(len(Trace)/Frequence),1.0/NewFrequence)
        return scipy.interpolate.interp1d(VectorPeriodTrace,Trace)(newVectorPeriodTrace)

    def makeTreatmentTraceBeforeNewFrequence(self, Trace, Frequence, remove_response, response_dict, config):
        """
        Return the trace treated with the function :func:`traces.TraceModules.tracesDefineTreatments.makeTreatmentTraceBeforeNewFrequence`
        in the module :mod:`traces.TraceModules.tracesDefineTreatments` **before** the resampling.
        """
        return tracesDefineTreatments.makeTreatmentTraceBeforeNewFrequence(Trace, Frequence, remove_response, response_dict, config)
        
    def makeTreatmentTraceAfterNewFrequence(self, Trace, Frequence, acorr, remove_response, response_dict, config):
        """
        Return the trace treated with the function :func:`traces.TraceModules.tracesDefineTreatments.makeTreatmentTraceAfterNewFrequence`
        in the module :mod:`traces.TraceModules.tracesDefineTreatments` **after** the resampling.
        """
        TraceW, TraceNoW = tracesDefineTreatments.makeTreatmentTraceAfterNewFrequence(Trace, Frequence, acorr, remove_response, response_dict, config)
        return TraceW, TraceNoW


