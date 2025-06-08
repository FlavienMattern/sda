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
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesFunctions
import obspy


def makeTreatmentTraceBeforeNewFrequence(Trace, Frequence, remove_response, response_dict, config):#Trace is destroyed
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


def makeTreatmentTraceAfterNewFrequence(Trace, Frequence, acorr, remove_response, response_dict, config):#Trace is destroyed
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
    ### Load some parameters
    Frequence = float(Frequence)
    numberOfSubTrace = config["numberOfSubTrace"]
    ratioZero = config["ratioZero"]
    ratioE = config["ratioE"]
    # clipping
    factorTestStdSeisme = config["factorTestStdSeisme"]
    # whitening
    freqMin = config["freqMin"]
    freqMax = config["freqMax"]
    periodMin  = 1.0/config["freqMax"]
    periodMax  = 1.0/config["freqMin"]
    divideFreq = config["divideFreq"]
    # border zeros (s)
    lengthBorder = config["lengthBorder"]
    
    ### Perform basic preprocessing using obspy before doing anything else
    tr = obspy.Trace(data=Trace)
    tr.stats.sampling_rate = Frequence
    tr.stats.starttime = obspy.UTCDateTime(2020,1,1) # Date doesn't matter, it is just to create a time vector to stream
    tr.detrend("demean")
    tr.detrend("spline", order=3, dspline=500)

    ### Remove response
    if remove_response:
        tr.stats.starttime = obspy.UTCDateTime(response_dict["start"])
        inventory = response_dict["inventory"]
        
        # Convert trace to obspy Trace object
        tr.stats.network = response_dict["station_name"].split(".")[0]
        tr.stats.station = response_dict["station_name"].split(".")[1]
        tr.stats.location = response_dict["station_name"].split(".")[2]
        tr.stats.channel = response_dict["station_name"].split(".")[3]
        
        # Attach and Remove response
        tr.attach_response(inventory)
        tr.remove_response(water_level=response_dict["water_level"],
                           pre_filt=response_dict["pre_filt"],
                           hide_sensitivity_mismatch_warning=True)
        
    # We only take the array for next steps
    Trace = tr.data

    ### Highpass filter
    freqmin = config["freqmin"]
    Trace = tracesFunctions.highPassFilter(Trace, freqmin, Frequence, corners = 4, zerophase=True)
   
    ### Glitch correction
    factorTestStd = config["factorTestStd"]
    numberOfStd = config["numberOfStd"]
    factorReplaceWithStd = config["factorReplaceWithStd"]
    Convergence = config["Convergence"]

    if Convergence == True:
        Trace = tracesFunctions.glitchCorrectionWithFactorStd(Trace, factorTestStd, numberOfStd, factorReplaceWithStd)
    else:
        Trace = tracesFunctions.glitchCorrectionWithFactorStdWithConvergence(Trace, factorTestStd, factorReplaceWithStd)

    ### Whitening/BandPass + SeismeCorrection
    TraceW, TraceNoW = tracesFunctions.MYmakeSubTreatment(Trace,numberOfSubTrace,Frequence,ratioE,ratioZero,periodMin,periodMax,freqMin,freqMax,divideFreq,factorTestStdSeisme,lengthBorder,acorr,config)
    
    return TraceW, TraceNoW
    
