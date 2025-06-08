################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Define the treatment of the traces.

Module tracesDefineTreatments
=============================

Specify a list of ordered processing for the traces for the functions 
:func:`makeTreatmentTraceBeforeNewFrequence` and :func:`makeTreatmentTraceAfterNewFrequence`. 
Functions can be import from the module :mod:`traces.TraceModules.tracesFunctions` or others available 
libraries as numpy, scipy, obspy, etc...

"""
import TraceModules.tracesFunctions

def makeTreatmentTraceBeforeNewFrequence(Trace, Frequence):#Trace is destroyed
    """
    Specify a list of ordered processing for the traces **before** resampling. Functions can be import from the
    module :mod:`traces.TraceModules.tracesFunctions` or others available libraries as numpy, scipy, obspy, etc...
    
    .. container:: 
        
        **Examples:**
        
            * Make treatment with a function :func:`foo` in the module :mod:`bar` with parameters p1, p2. Then add a code like this (verify the signature!):
            
                .. code-block:: python
                
                    p1 = aValue
                    p2 = None
                    Trace = bar.foo(Trace, p1, p2)
            
        
            * Filter the trace between 1 second and 3 seconds with the function :func:`filtfilt` (`see here`_) of the `library scipy`_ . Define also a Butterworth of order 3. Write:
            
            
                .. code-block:: python
                    
                    OrderButter = 3
                    PeriodMin = 1
                    PeriodMax = 3
                    arrayForButter = numpy.array([1./float(PeriodMax), 1./float(PeriodMin)])*2/float(Frequence)
                    b, a = scipy.signal.filter_design.iirfilter(OrderButter, arrayForButter)
                    Trace = scipy.signal.filtfilt(b, a, Trace)


    .. _library scipy: http://docs.scipy.org
    .. _see here: http://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.filtfilt.html
    """ 

    return Trace

def makeTreatmentTraceAfterNewFrequence(Trace, Frequence):#Trace is destroyed
    """
    Specify a list of ordered processing for the traces **after** resampling. Functions can be import from the
    module :mod:`traces.TraceModules.tracesFunctions` or others available libraries as scipy, obspy, etc...
    
    .. container:: 
        
        **Examples:**
        
            * Make a treatment with the function :func:`glitchCorrectionWithFactorStd` contains in the module :mod:`traces.TraceModules.tracesFunctions`:
            
                .. code-block:: python
                
                    factorTestStd = 10
                    numberOfStd = 3
                    factorReplaceWithStd = 0
                    Trace = TraceModules.tracesFunctions.glitchCorrectionWithFactorStd(Trace, factorTestStd, numberOfStd, factorReplaceWithStd)
            
        
            * Use the function :func:`highpass` of the `library obspy`_ :
            
                .. code-block:: python
                    
                    FreqMin = 50 #Hz
                    Order = 4
                    zerophase=True
                    Trace = obspy.signal.filter.highpass(Trace, FreqMin, Frequence, Order, zerophase)
                    
    .. _library obspy: http://docs.obspy.org/packages/autogen/obspy.signal.filter.highpass.html#obspy.signal.filter.highpass
    """
    Frequence = float(Frequence)

    print('highpass')
    ##HighpassFreqmin
    freqmin = 0.04
    Trace = TraceModules.tracesFunctions.highPassFilter(Trace, freqmin, Frequence, corners = 4, zerophase=True)

   
    print('glitch correction')
    ##FactorTestStd
    factorTestStd = 15
    ##NumberOfStd
    numberOfStd = 4
    ##FactorReplaceWithStd
    factorReplaceWithStd = 0
    ##Convergence
    Convergence = True

    if Convergence == True:
        Trace = TraceModules.tracesFunctions.glitchCorrectionWithFactorStd(Trace, factorTestStd, numberOfStd, factorReplaceWithStd)
    else:
        Trace = TraceModules.tracesFunctions.glitchCorrectionWithFactorStdWithConvergence(Trace, factorTestStd, factorReplaceWithStd)
        
       
    print('Trace cutting or makeSubTreatment')
    ##NumberOfSubTrace
    numberOfSubTrace = 96 
    # tranches de 15 min #WARNING: numberOfSubTrace must be a multiple of length(Trace)

    # CUT ?
    ##RatioZero
    ratioZero = 9.0/10.0
    ##RatioE
    ratioE    = 1.5

    # clipping
    ##FactorTestStdSeisme
    factorTestStdSeisme = 3.0

    # whitening
#    periodMin  = 0.04 #seconds
#    periodMax  = 5.0 #seconds
    ##Freqmin
    freqMin    = 0.04
    ##FreqMax
    freqMax    = 49.0
    ##PeriodMin
    periodMin  = 1.0/freqMax
    ##PeriodMax
    periodMax  = 1.0/freqMin
    ##DivideFreq
    divideFreq = 100.0

    # border zeros (s)
    ##LengthBorder
    lengthBorder = 100*Frequence

    Trace = TraceModules.tracesFunctions.MYmakeSubTreatment(Trace,numberOfSubTrace,Frequence,ratioE,ratioZero,periodMin,periodMax,freqMin,freqMax,divideFreq,factorTestStdSeisme,lengthBorder)
    return Trace
