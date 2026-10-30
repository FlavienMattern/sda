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
from sda.process.xcorr_noise.PreProcessingModules.TraceModules import tracesDefineTreatments


class TreatmentTrace():
    """
    Resample traces and apply the preprocessing workflow.
    
    .. Note::
    
        Precise workflow is defined in the module :mod:`traces.TraceModules.tracesDefineTreatments`.
    """
    def __init__(self, **kwargs):
        self.NewFrequence = kwargs['param'].NewFrequence
    
    def makeTreatment(self, Trace, Frequence, acorr, remove_response, response_dict, config):
        """
        Resample the trace, then apply the processing defined in tracesDefineTreatments.
        """
        Trace = self.makeNewFrequenceTrace(Trace, Frequence, self.NewFrequence)
        # Interpolation can add one endpoint because of floating point arange.
        Trace = Trace[:config["LenTrace"]]
        if len(Trace) != config["LenTrace"]:
            raise ValueError("Resampling did not produce the requested number of samples.")

        TraceW, TraceNoW = tracesDefineTreatments.makeTreatmentTraceAfterNewFrequence(Trace, self.NewFrequence, acorr, remove_response, response_dict, config)

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
        VectorPeriodTrace = numpy.arange(0, len(Trace)/float(Frequence), 1.0/float(Frequence))
        newVectorPeriodTrace = numpy.arange(0, len(Trace)/float(Frequence), 1.0/float(NewFrequence))
        return numpy.interp(newVectorPeriodTrace,VectorPeriodTrace,Trace)


