# -*- coding: utf-8 -*-
import sys
import numpy as np
import pickle as pkl
from math import ceil
from scipy.interpolate import interp1d
from obspy.signal.invsim import cosine_taper
from obspy.signal.regression import linear_regression
import scipy
from obspy.signal.filter import bandpass



####################################################
#                    FUNCTIONS                     #
####################################################

def stretching(ref, cur, dv_range, nbtrial, lagtime_range, para):
    """
    This function compares the Reference waveform to stretched/compressed current waveforms to get the
    relative seismic velocity variation (and associated error).
    It also computes the correlation coefficient between the Reference waveform and the current waveform.

    PARAMETERS:
    ----------------
    ref: Reference waveform (np.ndarray, size N)
    cur: Current waveform (np.ndarray, size N)
    dv_range: absolute bound for the velocity variation; example: dv=0.03 for [-3,3]%
    of relative velocity change ('float')
    nbtrial: number of stretching coefficient between dvmin and dvmax, no need to be higher than 100  ('float')
    para: vector of the indices of the cur and ref windows on wich you want to do the measurements
    (np.ndarray, size tmin*delta:tmax*delta)
    For error computation, we need parameters:
        fmin: minimum frequency of the data
        fmax: maximum frequency of the data
        tmin: minimum time window where the dv/v is computed
        tmax: maximum time window where the dv/v is computed
    RETURNS:
    ----------------
    dv: Relative velocity change dv/v (in %)
    cc: correlation coefficient between the reference waveform and the best stretched/compressed current waveform
    cdp: correlation coefficient between the reference waveform and the initial current waveform
    error: Errors in the dv/v measurements based on Weaver et al (2011),
    On the precision of noise-correlation interferometry, Geophys. J. Int., 185(3)

    Note: The code first finds the best correlation coefficient between the Reference waveform and
    the stretched/compressed current waveform among the "nbtrial" values.
    A refined analysis is then performed around this value to obtain a more precise dv/v measurement .

    Originally by L. Viens 04/26/2018 (Viens et al., 2018 JGR)
    modified by Chengxin Jiang
    """
    # load common variables from dictionary
    freq = para["freq"]
    dt = para["dt"]
    fmin = np.min(freq)
    fmax = np.max(freq)
    tvec = np.linspace(min(para["twin"]), max(para["twin"]), len(cur))
    lagtime = np.linspace(min(para["twin"]), max(para["twin"]), len(cur))
    
    # Filter correlations
    ref = bandpass(ref, fmin, fmax, 1/dt, corners=4, zerophase=True)  # A DECOMMENTER SI BESOIN
    cur = bandpass(cur, fmin, fmax, 1/dt, corners=4, zerophase=True)  # A DECOMMENTER SI BESOIN
    
    # Results dictionnary
    stretchingResults = {}

    # make useful one for measurements
    dvmin = -np.abs(dv_range)
    dvmax = np.abs(dv_range)
    Eps = np.linspace(dvmin, dvmax, nbtrial)
        
    if len(np.shape(lagtime_range)) == 1:
        lagtime_range = [lagtime_range]
        
    # Loop over all lagtime windows    
    for lag in lagtime_range:
        lagtimeMin = min(lag)
        lagtimeMax = max(lag)
        
        tmin = min(lag)
        tmax = max(lag)
        
        lagstr = "{:.2f}_{:.2f}s".format(lagtimeMin, lagtimeMax)
        cof = np.zeros(Eps.shape, dtype=np.float32)

        # Set of stretched/compressed current waveforms
        for ii in range(len(Eps)):
            nt = tvec * (1 - Eps[ii])
            s = np.interp(x=tvec, xp=nt, fp=cur)
            waveform_ref = ref
            waveform_cur = s
            ### Cutting for specific lagtime
            idx1 = np.where(lagtime >= lagtimeMin)
            idx2 = np.where(lagtime <= lagtimeMax)
            idx = np.intersect1d(idx1,idx2)
            waveform_ref = waveform_ref[idx]
            waveform_cur = waveform_cur[idx]
            ###
            cof[ii] = np.corrcoef(waveform_ref, waveform_cur)[0, 1]
            
        cdp = np.corrcoef(cur, ref)[0, 1]  # correlation coefficient between the reference and initial current waveforms

        # find the maximum correlation coefficient
        imax = np.nanargmax(cof)
        if imax >= len(Eps) - 2:
            imax = imax - 2
        if imax <= 2:
            imax = imax + 2      
            
        # Proceed to the second step to get a more precise dv/v measurement
        dtfiner = np.linspace(Eps[imax - 2], Eps[imax + 2], nbtrial)
        ncof = np.zeros(dtfiner.shape, dtype=np.float32)
        for ii in range(len(dtfiner)):
            nt = tvec * (1 - dtfiner[ii])
            s = np.interp(x=tvec, xp=nt, fp=cur)
            waveform_ref = ref
            waveform_cur = s
            ### Cutting for specific lagtime
            idx1 = np.where(lagtime >= lagtimeMin)
            idx2 = np.where(lagtime <= lagtimeMax)
            idx = np.intersect1d(idx1,idx2)
            waveform_ref = waveform_ref[idx]
            waveform_cur = waveform_cur[idx]
            ###
            ncof[ii] = np.corrcoef(waveform_ref, waveform_cur)[0, 1]

        cc = np.max(ncof)  # Find maximum correlation coefficient of the refined  analysis
        dv = 100.0 * dtfiner[np.argmax(ncof)]  # Multiply by 100 to convert to percentage (Epsilon = -dt/t = dv/v)

        # Error computation based on Weaver et al (2011), On the precision of noise-correlation
        # interferometry, Geophys. J. Int., 185(3)
        T = 1 / (fmax - fmin)
        X = cc
        wc = np.pi * (fmin + fmax)
        t1 = np.min([tmin, tmax])
        t2 = np.max([tmin, tmax])
        error = 100 * (
            np.sqrt(1 - X**2) / (2 * X) * np.sqrt((6 * np.sqrt(np.pi / 2) * T) / (wc**2 * (t2**3 - t1**3)))
        )
        
        stretchingResults[lagstr] = {}
        stretchingResults[lagstr]["dv"] = -dv
        stretchingResults[lagstr]["error"] = error
        stretchingResults[lagstr]["cc"] = cc
        stretchingResults[lagstr]["cdp"] = cdp

    return stretchingResults



def mwcs(ref, cur, moving_window_length, slide_step, para, lagtime_range, smoothing_half_win=5):
    """
    Moving Window Cross Spectrum method to measure dv/v (relying on phi=2*pi*f*t in freq domain)

    PARAMETERS:
    ----------------
    ref: Reference waveform (np.ndarray, size N)
    cur: Current waveform (np.ndarray, size N)
    moving_window_length: moving window length to calculate cross-spectrum (np.float, in sec)
    slide_step: steps in time to shift the moving window (np.float, in seconds)
    para: a dict containing parameters about input data window and frequency info, including
        delta->The sampling rate of the input timeseries (in Hz)
        window-> The target window for measuring dt/t
        freq-> The frequency bound to compute the dephasing (in Hz)
        tmin: The leftmost time lag (used to compute the "time lags array")
    smoothing_half_win: If different from 0, defines the half length of the smoothing hanning window.

    RETURNS:
    ------------------
    dv/v as - dt/t as a float
    errors as the standard deviation of the linear regression

    Modified from MSNoise (https://github.com/ROBelgium/MSNoise/tree/master/msnoise)
    Modified by Chengxin Jiang
    Changed by Marine Denolle (mdenolle@uw.edu) 9/23
    """
    # common variables
    
    twin = para["twin"]
    freq = para["freq"]
    dt = para["dt"]
    tmin = np.min(twin)
    fmin = np.min(freq)
    fmax = np.max(freq)
    lagtime = twin
    
    # Filter correlations
    ref = bandpass(ref, fmin, fmax, 1/dt, corners=4, zerophase=True)
    cur = bandpass(cur, fmin, fmax, 1/dt, corners=4, zerophase=True)

    # Results dictionnary
    mwcsResults = {}

    # parameter initialize
    delta_t = []
    delta_err = []
    delta_mcoh = []
    time_axis = []
    
    # info on the moving window
    window_length_samples = int(moving_window_length / dt)
    padd = int(2 ** (nextpow2(window_length_samples) + 2))
    count = 0
    tp = cosine_taper(window_length_samples, 0.15)

    minind = 0
    maxind = window_length_samples

    # loop through all sub-windows
    while maxind <= len(ref):
        
        cci = cur[minind:maxind]
        cci = scipy.signal.detrend(cci, type="linear")
        cci *= tp

        cri = ref[minind:maxind]
        cri = scipy.signal.detrend(cri, type="linear")
        cri *= tp

        minind += int(slide_step / dt)
        maxind += int(slide_step / dt)

        # do fft
        fcur = scipy.fftpack.fft(cci, n=padd)[: padd // 2]
        fref = scipy.fftpack.fft(cri, n=padd)[: padd // 2]

        fcur2 = np.real(fcur) ** 2 + np.imag(fcur) ** 2
        fref2 = np.real(fref) ** 2 + np.imag(fref) ** 2

        # get cross-spectrum & do filtering
        X = fref * (fcur.conj())
        if smoothing_half_win != 0:
            dcur = np.sqrt(smooth(fcur2, window="hanning", half_win=smoothing_half_win))
            dref = np.sqrt(smooth(fref2, window="hanning", half_win=smoothing_half_win))
            X = smooth(X, window="hanning", half_win=smoothing_half_win)
        else:
            dcur = np.sqrt(fcur2)
            dref = np.sqrt(fref2)

        dcs = np.abs(X)

        # Find the values the frequency range of interest
        freq_vec = scipy.fftpack.fftfreq(len(X) * 2, dt)[: padd // 2]
        index_range = np.argwhere(np.logical_and(freq_vec >= fmin, freq_vec <= fmax))

        # Get Coherence and its mean value
        coh = getCoherence(dcs, dref, dcur)
        mcoh = np.mean(coh[index_range])

        # Get Weights
        w = 1.0 / (1.0 / (coh[index_range] ** 2) - 1.0)
        w[coh[index_range] >= 0.99] = 1.0 / (1.0 / 0.9801 - 1.0)
        w = np.sqrt(w * np.sqrt(dcs[index_range]))
        w = np.real(w)

        # Frequency array:
        v = np.real(freq_vec[index_range]) * 2 * np.pi

        # Phase:
        phi = np.angle(X)
        phi[0] = 0.0
        phi = np.unwrap(phi)
        phi = phi[index_range]

        # Calculate the slope with a weighted least square linear regression
        # forced through the origin; weights for the WLS must be the variance !
        m, em = linear_regression(v.flatten(), phi.flatten(), w.flatten())
        delta_t.append(m)

        # print phi.shape, v.shape, w.shape
        e = np.sum((phi - m * v) ** 2) / (np.size(v) - 1)
        s2x2 = np.sum(v**2 * w**2)
        sx2 = np.sum(w * v**2)
        e = np.sqrt(e * s2x2 / sx2**2)

        delta_err.append(e)
        delta_mcoh.append(np.real(mcoh))
        time_axis.append(tmin + moving_window_length / 2.0 + count * slide_step)
        count += 1


        del fcur, fref
        del X
        del freq_vec
        del index_range
        del w, v, e, s2x2, sx2, m, em

    # if maxind > len(cur) + int(slide_step / dt):
    #     print("The last window was too small, but was computed")

    # ensure all matrix are np array
    delta_t = np.array(delta_t)
    delta_err = np.array(delta_err)
    delta_mcoh = np.array(delta_mcoh)
    time_axis = np.array(time_axis)
    
    if len(np.shape(lagtime_range)) == 1:
        lagtime_range = [lagtime_range]

    # Loop over all lagtime windows
    for lag in lagtime_range:
        lagtimeMin = min(lag)
        lagtimeMax = max(lag)
        lagstr = "{:.2f}_{:.2f}s".format(lagtimeMin, lagtimeMax)

        # ready for linear regression
        delta_mincho = 0.65
        delta_maxerr = 0.1
        delta_maxdt = 0.1
        # indx1 = np.where(delta_mcoh > delta_mincho)
        # indx2 = np.where(delta_err < delta_maxerr)
        # indx3 = np.where(delta_t < delta_maxdt)
        indx1 = np.where(time_axis >= lagtimeMin)
        indx2 = np.where(time_axis <= lagtimeMax)

        # -----find good dt measurements-----
        indx = np.intersect1d(indx1, indx2)
        # indx = np.intersect1d(indx, indx3)

        if len(indx) > 2:
            # ----estimate weight for regression----
            w = 1 / delta_err[indx]
            w[~np.isfinite(w)] = 1.0

            # ---------do linear regression-----------
            # m, a, em, ea = linear_regression(time_axis[indx], delta_t[indx], w, intercept_origin=False)
            m0, em0 = linear_regression(time_axis[indx], delta_t[indx], w, intercept_origin=True)
            idx1 = np.where(lagtime >= lagtimeMin)
            idx2 = np.where(lagtime <= lagtimeMax)
            idx = np.intersect1d(idx1,idx2)
            cci = cur[idx]
            cri = ref[idx]
            cc = np.corrcoef(cci, cri)[0, 1]

        else:
            print("not enough points to estimate dv/v for mwcs")
            m0 = np.nan
            em0 = np.nan
            cc = np.nan
            
        mwcsResults[lagstr] = {}
        mwcsResults[lagstr]["dv"] = -m0 * 100
        mwcsResults[lagstr]["error"] = em0 * 100
        mwcsResults[lagstr]["cc"] = cc

    return mwcsResults




def nextpow2(x):
    """
    Returns the next power of 2 of x.
    """
    return int(np.ceil(np.log2(np.abs(x))))



def getCoherence(dcs, ds1, ds2):
    """
    get cross coherence between reference and current waveforms following equation of A3 in Clark et al., 2011

    Parameters
    --------------
    dcs: amplitude of the cross spectrum
    ds1: amplitude of the spectrum of current waveform
    ds2: amplitude of the spectrum of reference waveform

    RETURNS:
    ------------------
    coh: cohrerency matrix used for estimate the robustness of the cross spectrum
    """
    n = len(dcs)
    coh = np.zeros(n).astype("complex")
    valids = np.argwhere(np.logical_and(np.abs(ds1) > 0, np.abs(ds2) > 0))
    coh[valids] = dcs[valids] / (ds1[valids] * ds2[valids])
    coh[coh > (1.0 + 0j)] = 1.0 + 0j
    return coh



def smooth(x, window="boxcar", half_win=3):
    """
    performs smoothing in interested time window

    Parameters
    --------------
    x: timeseris data
    window: types of window to do smoothing
    half_win: half window length

    RETURNS:
    ------------------
    y: smoothed time window
    """
    # TODO: docsting
    window_len = 2 * half_win + 1
    # extending the data at beginning and at the end
    # to apply the window at the borders
    s = np.r_[x[window_len - 1 : 0 : -1], x, x[-1:-window_len:-1]]
    if window == "boxcar":
        w = scipy.signal.boxcar(window_len).astype("complex")
    else:
        w = scipy.signal.windows.hann(window_len).astype("complex")
    y = np.convolve(w / w.sum(), s, mode="valid")
    return y[half_win : len(y) - half_win]