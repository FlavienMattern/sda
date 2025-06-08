################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Provides some functions for the processing of traces. 

Module tracesFunctions
======================

"""
import numpy
import numpy as np
import scipy.fftpack
import scipy.signal
import obspy.signal
from obspy.signal.filter import bandpass
import copy
from datetime import datetime, timedelta
from obspy import UTCDateTime

import scipy.fft as sf
from scipy.fft import next_fast_len

def butter_bandpass(lowcut, highcut, fs, order=5):
    return butter(order, [lowcut, highcut], fs=fs, btype='band')

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def witheningCosEnergy(Trace, FreqMin, FreqMax, FreqSampling, dt):#ok at 10e-8 same as matlab blanc(Trace,FreqMin,FreqMax,FreqSampling,'cos',dt);
    """
    Return the trace whitened with an apodization in cosinus square and multiply by the root square of the energy.
    
    :Parameters:
        **Trace**: numpy array
            The trace to be whitened.
        **FreqMin**, **FreqMax**: float
            The frequency minimal and the frequency maximal which define the interval.
        **FreqSampling**: float
            The frequency of the sampling.
        **dt**: float
            The percentage of the length of the apodization of each border.
    """
    n1 = int(round(FreqMin*len(Trace)/FreqSampling+1))
    n2 = int(round(FreqMax*len(Trace)/FreqSampling+1))
    apod = numpy.ones(n2 - n1 + 1)
    na1 = round(dt/FreqSampling*len(Trace))
    #left border
    border = numpy.arange(1,int(na1)+1)/na1/2*numpy.pi
    border = numpy.square(numpy.sin(border))
    apod[0:int(na1)] = border
    #rigth border
    border = numpy.arange(int(na1)+1,2*na1+1)/na1/2*numpy.pi
    border = numpy.square(numpy.sin(border))
    apod[-int(na1):]= border
    spectre = scipy.fftpack.fft(Trace)
    E = numpy.sqrt(numpy.sum(numpy.absolute(numpy.square(spectre[n1-1:n2]))))/(n2-n1+1)
    spectre[n1-1:n2] = numpy.exp(1j*numpy.angle(spectre[n1-1:n2]))*apod*E
    spectre[0:n1-1] = 0
    spectre[n2:] = 0
    return 2*scipy.fftpack.ifft(spectre).real

def witheningCos(Trace, freqMin, freqMax, FreqSampling, DivideFreq):
    """
    Return the trace whitened with an apodization in cosinus square.
    
    :Parameters:
        **Trace**: numpy array
            The trace to be whitened.
        **freqMin**, **freqMax**: float
            The frequency minimal and the frequency maximal which define the interval.
        **FreqSampling**: float
            The frequency of the sampling.
        **DivideFreq**: float
            The percentage of the length of the apodization of each border.
            
    """
    IndexWhiteMin, IndexWhiteMax, LengthApodisation, BorderLeft, BorderRight, NoramisationWithening = \
        preparewitheningCos(len(Trace), freqMin, freqMax, FreqSampling, DivideFreq)
    return witheningCosPrepared(Trace, IndexWhiteMin, IndexWhiteMax, LengthApodisation, BorderLeft, BorderRight, NoramisationWithening)

def witheningCosPrepared(Trace, IndexWhiteMin, IndexWhiteMax, LengthApodisation, BorderLeft, BorderRight, NormalisationWithening):
    TraceWitened =  numpy.zeros(len(Trace), dtype='complex')
    TraceWitened[IndexWhiteMin:IndexWhiteMax] = scipy.fftpack.fft(Trace)[IndexWhiteMin:IndexWhiteMax]
    TraceWitened[IndexWhiteMin:IndexWhiteMax] /= numpy.absolute(TraceWitened[IndexWhiteMin:IndexWhiteMax])*NormalisationWithening
    TraceWitened[IndexWhiteMin:IndexWhiteMin+int(LengthApodisation)] *= BorderLeft
    TraceWitened[IndexWhiteMax-int(LengthApodisation):IndexWhiteMax] *= BorderRight
    TRWI = ((scipy.fftpack.ifft(TraceWitened, overwrite_x=True)).real)
    return TRWI


def preparewitheningCos(LengthTrace, freqMin, freqMax, FreqSampling, DivideFreq):
    dt = (freqMax - freqMin)*DivideFreq
    IndexWhiteMin = int(round(freqMin*LengthTrace/FreqSampling+1))-1
    IndexWhiteMax = int(round(freqMax*LengthTrace/FreqSampling+1))
    LengthApodisation = round(dt/FreqSampling*LengthTrace)
    BorderLeft = numpy.square(numpy.sin(numpy.arange(1,int(LengthApodisation)+1)/LengthApodisation/2*numpy.pi))
    BorderRight = numpy.square(numpy.sin(numpy.arange(int(LengthApodisation)+1,2*LengthApodisation+1)/LengthApodisation/2*numpy.pi))
    NoramisationWithening = numpy.sqrt(float(IndexWhiteMax-IndexWhiteMin-5*LengthApodisation/4)/LengthTrace/2)
    return IndexWhiteMin, IndexWhiteMax, LengthApodisation, BorderLeft, BorderRight, NoramisationWithening

'''
def MY_witheningCos(Trace, freqMin, freqMax, FreqSampling, DivideFreq):
    """
    Return the trace whitened with an apodization in cosinus square.
    
    :Parameters:
        **Trace**: numpy array
            The trace to be whitened.
        **freqMin**, **freqMax**: float
            The frequency minimal and the frequency maximal which define the interval.
        **FreqSampling**: float
            The frequency of the sampling.
        **DivideFreq**: float
            The percentage of the length of the apodization of each border.
            
    """
    IndexWhiteMin, IndexWhiteMax, LengthApodisationR, LengthApodisationL, BorderLeft, BorderRight, NoramisationWithening = \
        MY_preparewitheningCos(len(Trace), freqMin, freqMax, FreqSampling, DivideFreq)
    return MY_witheningCosPrepared(Trace, IndexWhiteMin, IndexWhiteMax, LengthApodisationR, LengthApodisationL, BorderLeft, BorderRight, NoramisationWithening)

def MY_witheningCosPrepared(Trace, IndexWhiteMin, IndexWhiteMax, LengthApodisationR, LengthApodisationL, BorderLeft, BorderRight, NormalisationWithening):
    TraceWitened =  numpy.zeros(len(Trace), dtype='complex')
    TraceWitened[IndexWhiteMin:IndexWhiteMax] = scipy.fftpack.fft(Trace)[IndexWhiteMin:IndexWhiteMax]
    TraceWitened[IndexWhiteMin:IndexWhiteMax] /= numpy.absolute(TraceWitened[IndexWhiteMin:IndexWhiteMax])*NormalisationWithening
    TraceWitened[IndexWhiteMin:IndexWhiteMin+int(LengthApodisationL)] *=  BorderLeft
    TraceWitened[IndexWhiteMax-int(LengthApodisationR):IndexWhiteMax] *= BorderRight
    return ((scipy.fftpack.ifft(TraceWitened, overwrite_x=True)).real)

def MY_preparewitheningCos(LengthTrace, freqMin, freqMax, FreqSampling, DivideFreq):
    dt = (freqMax - freqMin)/DivideFreq
    IndexWhiteMin = int(round(freqMin*LengthTrace/FreqSampling+1))-1
    IndexWhiteMax = int(round(freqMax*LengthTrace/FreqSampling+1))
    LengthApodisationR = round(dt/FreqSampling*LengthTrace)*100.0
    LengthApodisationL = round(dt/FreqSampling*LengthTrace)
    BorderLeft = numpy.square(numpy.sin(numpy.arange(1,int(LengthApodisationL)+1)/LengthApodisationL/2*numpy.pi))
    BorderRight = numpy.square(numpy.sin(numpy.arange(int(LengthApodisationR)+1,2*LengthApodisationR+1)/LengthApodisationR/2*numpy.pi))
    NoramisationWithening = numpy.sqrt(float(IndexWhiteMax-IndexWhiteMin-5*LengthApodisationR/4)/LengthTrace/2)
    return IndexWhiteMin, IndexWhiteMax, LengthApodisationR, LengthApodisationL, BorderLeft, BorderRight, NoramisationWithening
'''

def makeButterFromPeriods(PeriodMin, PeriodMax, FreqSamplingRate, OrderButter):
    return scipy.signal.filter_design.iirfilter(OrderButter, numpy.array([1./float(PeriodMax), 1./float(PeriodMin)])*2/float(FreqSamplingRate))

def makeFiltfiltAndButterFromPeriod(Trace, PeriodMin, PeriodMax, SamplingRate, OrderButter):
    """
    Return the trace filtered with zerophase.
    
    :Parameters:
        **Trace**: numpy array
            The trace to be filtered.
        **PeriodMin**, **PeriodMax**: float
            The period minimal and the period maximal which define the interval.
        **SamplingRate**: float
            The frequency of the sampling.
        **OrderButter**: int
            The order of the butterworth.
            
    """
    b,a = makeButterFromPeriods(PeriodMin, PeriodMax, SamplingRate, OrderButter)
    return scipy.signal.filtfilt(b, a, Trace)

def makeFiltfilt(Trace, b, a):
    return scipy.signal.filtfilt(b, a, Trace)

def makeSign(Trace):
    """
    Return the array of the sign of the trace. Trace is destroyed. 
    :Parameters:
        **Trace**: numpy array
            The trace from which get the sign.
    """
    return np.sign(Trace)

def glitchCorrectionWithFactorStd(Trace, FactorTestStd, NumberOfStd = 1, FactorReplaceWithStd = 0):#Trace is destroyed
    """
    make doc!!!!
    """
    Std_tab = []
    Std_tab.append(numpy.std(Trace))
        
    for i in range(NumberOfStd):
        arrayReplace = numpy.ones(len(Trace), dtype ='float')*numpy.std(Trace)*FactorReplaceWithStd
        arrayReplace *= numpy.sign(Trace)
        Trace = numpy.where(numpy.absolute(Trace)>FactorTestStd*numpy.std(Trace), arrayReplace, Trace)
        Std_tab.append(numpy.std(Trace))
        
    return Trace

def glitchCorrectionWithFactorStdWithConvergence(Trace, FactorTestStd, FactorReplaceWithStd = 0):#Trace is destroyed
    """
    make doc!!!!
    """
    Std_tab = []
    Std_tab.append(numpy.std(Trace))

    arrayReplace = numpy.ones(len(Trace), dtype = 'float')*numpy.std(Trace)*FactorReplaceWithStd
    arrayReplace *= numpy.sign(Trace)
    tr2 = numpy.where(numpy.absolute(Trace)>FactorTestStd*numpy.std(Trace), arrayReplace, Trace)
    Std_tab.append(numpy.std(tr2))

    count = 0
    while (not numpy.min(tr2 == Trace)) and count<100:#It exists a value different in Trace and tr2
        Trace = tr2
        arrayReplace = numpy.ones(len(Trace), dtype = 'float')*numpy.std(Trace)*FactorReplaceWithStd
        arrayReplace *= numpy.sign(Trace)
        tr2 = numpy.where(numpy.absolute(Trace)>FactorTestStd*numpy.std(Trace), arrayReplace, Trace)
        Std_tab.append(numpy.std(tr2))
        count += 1

    return tr2

def makeBorderZero(Trace, LengthBorderLeft, LengthBorderRigth=None):
    """
    Return the trace with the border replaced by zeros.
    
    :Parameters:
        **Trace**: numpy array
            The trace to be filtered.
        **LengthBorderLeft**: int
            The length of the left border which is setting to zero.
        **LengthBorderRigth**: int (optional)
            The length of the rigth border which is setting to zero. Default is LengthBorderLeft.
            
    """
    if LengthBorderRigth is None:
        LengthBorderRigth=LengthBorderLeft
    Trace[0:LengthBorderLeft]=0
    Trace[-LengthBorderRigth:]=0
    return Trace

def highPassFilter(data, freq, df, corners = 4, zerophase=True):
    import numpy as np
    from scipy.fftpack import hilbert
    from scipy.signal import (cheb2ord, cheby2, convolve, get_window, iirfilter, remez)
    
    try:
        from scipy.signal import sosfilt
        from scipy.signal import zpk2sos
    except ImportError:
        from ._sosfilt import _sosfilt as sosfilt
        from ._sosfilt import _zpk2sos as zpk2sos

    """
    Butterworth-Highpass Filter.

    Filter data removing data below certain frequency ``freq`` using
    ``corners`` corners.
    The filter uses :func:`scipy.signal.iirfilter` (for design)
    and :func:`scipy.signal.sosfilt` (for applying the filter).

    :type data: numpy.ndarray
    :param data: Data to filter.
    :param freq: Filter corner frequency.
    :param df: Sampling rate in Hz.
    :param corners: Filter corners / order.
    :param zerophase: If True, apply filter once forwards and once backwards.
        This results in twice the number of corners but zero phase shift in
        the resulting filtered trace.
    :return: Filtered data.
    """
    fe = 0.5 * df
    f = freq / fe
    # raise for some bad scenarios
    if f > 1:
        msg = "Selected corner frequency is above Nyquist."
        raise ValueError(msg)
    z, p, k = iirfilter(corners, f, btype='highpass', ftype='butter',
                        output='zpk')
    sos = zpk2sos(z, p, k)
    if zerophase:
        firstpass = sosfilt(sos, data)
        return sosfilt(sos, firstpass[::-1])[::-1]
    else:
        return sosfilt(sos, data)

def MYseismeCorrectionWithFactorStdWithConvergence(Trace, FactorTestStd, FactorReplaceWithStd = 0):
    std1 = numpy.std(Trace[0:int(numpy.round(len(Trace)/3))])
    std2 = numpy.std(Trace[int(numpy.round(len(Trace)/3)):2*int(numpy.round(len(Trace)/3))])
    std3 = numpy.std(Trace[0:int(numpy.round(len(Trace)))])
    minstd = numpy.amin([std1, std2, std3])       
    arrayReplace = numpy.ones(len(Trace), dtype = 'float')*minstd*FactorReplaceWithStd
    arrayReplace *= numpy.sign(Trace)
    tr2 = numpy.where(numpy.absolute(Trace)>FactorTestStd*minstd, arrayReplace, Trace)
    count = 0
    while (not numpy.min(tr2 == Trace)) and count<100:#It exists a value different in Trace and tr2
        Trace = tr2
        arrayReplace = numpy.ones(len(Trace), dtype = 'float')*minstd*FactorReplaceWithStd
        arrayReplace *= numpy.sign(Trace)
        tr2 = numpy.where(numpy.absolute(Trace)>FactorTestStd*minstd, arrayReplace, Trace)
        count += 1
        
    return tr2

def MYmeanEnergy(Trace,numberOfSubTrace):
    aminiE=numpy.zeros(numberOfSubTrace, dtype = 'float')
    inc = 0
    for i in range(numberOfSubTrace):	
        SubTrace = Trace[i*int(len(Trace)/numberOfSubTrace):(i+1)*int(len(Trace)/numberOfSubTrace)]
        if  numpy.size(numpy.where(numpy.absolute(SubTrace) > (10**-10)),axis=1) > 9*len(SubTrace)/10:
            aminiE[inc]=numpy.sum(numpy.power(SubTrace,2))/len(SubTrace)            
	    
        inc = inc + 1
    if numpy.amax(aminiE) == 0:
        E = 0
    else:
        E = numpy.sum(aminiE[numpy.where(aminiE > 0)])/(inc+1)
    return E

def MYsubTreatment(Trace,Frequence,STD,factorTestE,ratioZero,periodMin,periodMax,freqMin,freqMax,divideFreq,factorTestStdSeisme,lengthBorder,acorr, config):
    std = numpy.std(Trace)
    arrayReplace = numpy.zeros(len(Trace), dtype = 'float')
    
    if numpy.sum(numpy.power(Trace,2))/len(Trace) > factorTestE or numpy.size(numpy.where(numpy.absolute(Trace) > (10**-10)),axis=1) < ratioZero*len(Trace):
        # 2 conditions
        # 1) SOIT l'energie dépasse le seuil factorTestE
        # 2) SOIT j'ai plus de <ratioZero>% de la subtrace sans données
        # -> si c'est le cas, je ne garde pas la subtrace
        ### Cut subtrace
        Trace = arrayReplace
        return Trace, Trace
    
    else:
        factorReplaceWithStd = factorTestStdSeisme
        
        # Bandpass filter
        # Trace = bandpass(Trace, freqMin, freqMax, Frequence, corners=4, zerophase=True)
        
        # Onebit clipping
        if config["do1bit"] == "before_whiten":
            Trace = makeSign(Trace) 
        
        ### Whitening
        TraceW = witheningCos(Trace, freqMin, freqMax, Frequence, divideFreq)
        # TraceNoW = Trace.copy() # No whitening for autocorrelation
        TraceNoW = bandpass(Trace, freqMin, freqMax, Frequence, corners=4, zerophase=True) # Bandpass filter

        #############################
        # import pickle as pkl
        # import os
        # foldername = os.path.join("/media/flavien/WORK/these/schema/RESULTS/workflow_data",
        #                           config["response_dict"]["station_name"].split(".")[1],
        #                           config["response_dict"]["start"].strftime("%Y-%m-%d"),
        #                           f"subwindows")
        # filename = os.path.join(foldername, f"{config['iteration']}_white.pkl")
        # print(filename)
        # with open(filename, "wb") as f:
        #     pkl.dump(TraceW, f)
        #############################
        
        # Onebit clipping
        if config["do1bit"] == "after_whiten":
            TraceW = makeSign(TraceW) 
            TraceNoW = makeSign(TraceNoW) 
        
        
        # Earthquake correction
        TraceW = MYseismeCorrectionWithFactorStdWithConvergence(TraceW, factorTestStdSeisme, factorReplaceWithStd)
        TraceNoW = MYseismeCorrectionWithFactorStdWithConvergence(TraceNoW, factorTestStdSeisme, factorReplaceWithStd)

        return TraceW, TraceNoW

def MYmakeSubTreatment(Trace,numberOfSubTrace,Frequence,ratioE,ratioZero,periodMin,periodMax,freqMin,freqMax,divideFreq,factorTestStdSeisme,lengthBorder,acorr,config):	
    
    factorTestE = ratioE * MYmeanEnergy(Trace,numberOfSubTrace)
    STD = numpy.std(Trace)
    SubLenTrace = int(len(Trace)/float(numberOfSubTrace))
    if acorr == True:
        TraceW = copy.deepcopy(Trace)
        TraceNoW = copy.deepcopy(Trace)
           
    if isinstance(config["restricted_times"], list):
        if len(config["restricted_times"]) > 0: 
            do_restricted_times = True
            # print("Preparing subtreatment...")
            starttime = datetime.strptime(config["starttime"], "%Y-%m-%d")
            endtime = datetime.strptime(config["endtime"], "%Y-%m-%d")
            # print("> starttime", starttime)
            # print("> endtime", endtime)
            restricted_times = [(UTCDateTime(t1).datetime, UTCDateTime(t2).datetime) for t1, t2 in config["restricted_times"]]
        else:
            do_restricted_times = False
    else:
        do_restricted_times = False 
        
    hourMin = config["HourFilter"][0] * 60
    hourMax = config["HourFilter"][1] * 60   

    for i in range(numberOfSubTrace):
        windowStart = i     * SubLenTrace/Frequence/60 # Begin of the window (in min)
        windowEnd   = (i+1) * SubLenTrace/Frequence/60 # End of the window (in min)
        currentHour = (windowStart + windowEnd) / 2
        config["iteration"] = i
        
        
        if do_restricted_times:
            start_sub = starttime + timedelta(minutes=windowStart)
            end_sub   = starttime + timedelta(minutes=windowEnd)
            isInRestrictedTimes = any(ref_start <= start_sub and end_sub <= ref_end for ref_start, ref_end in restricted_times)
        else:
            isInRestrictedTimes = True
        
        # Check if sublen is in choosen hours
        if hourMin < hourMax:
            if currentHour >= hourMin and currentHour <= hourMax:
                isInHours = True
            else:
                isInHours = False
        else:
            if currentHour >= hourMin or currentHour <= hourMax:
                isInHours = True
            else:
                isInHours = False
        
        #############################
        # import pickle as pkl
        # import os
        # foldername = os.path.join("/media/flavien/WORK/these/schema/RESULTS/workflow_data",
        #                           config["response_dict"]["station_name"].split(".")[1],
        #                           config["response_dict"]["start"].strftime("%Y-%m-%d"),
        #                           f"subwindows")
        # try: 
        #     os.makedirs(foldername)
        # except:
        #     pass
        # filename = os.path.join(foldername, f"{i}_raw.pkl")
        # print(filename)
        # with open(filename, "wb") as f:
        #     pkl.dump(Trace[i*SubLenTrace:(i+1)*SubLenTrace], f)
        #############################
        
        if isInHours and isInRestrictedTimes:
            # print(f"    {i+1} : {start_sub} - {end_sub}     -->    Processing")
            subTraceW, subTraceNoW = MYsubTreatment(Trace[i*SubLenTrace:(i+1)*SubLenTrace],Frequence,STD,factorTestE,ratioZero,periodMin,periodMax,freqMin,freqMax,divideFreq,factorTestStdSeisme,lengthBorder,acorr, config)
            TraceW[i*SubLenTrace:(i+1)*SubLenTrace] = subTraceW
            TraceNoW[i*SubLenTrace:(i+1)*SubLenTrace] = subTraceNoW
            
        else:
            # print(f"    {i+1} : {start_sub} - {end_sub}     -->    NOT Processing")
            TraceW[i*SubLenTrace:(i+1)*SubLenTrace] = TraceW[i*SubLenTrace:(i+1)*SubLenTrace]*0
            TraceNoW[i*SubLenTrace:(i+1)*SubLenTrace] = TraceNoW[i*SubLenTrace:(i+1)*SubLenTrace]*0

        #############################
        # import pickle as pkl
        # import os
        # foldername = os.path.join("/media/flavien/WORK/these/schema/RESULTS/workflow_data",
        #                           config["response_dict"]["station_name"].split(".")[1],
        #                           config["response_dict"]["start"].strftime("%Y-%m-%d"),
        #                           f"subwindows")
        # filename = os.path.join(foldername, f"{i}_eqcorr.pkl")
        # print(filename)
        # with open(filename, "wb") as f:
        #     pkl.dump(TraceW[i*SubLenTrace:(i+1)*SubLenTrace], f)
        #############################
      
    return TraceW, TraceNoW
