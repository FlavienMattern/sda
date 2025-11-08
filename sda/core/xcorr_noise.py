import h5py
import numpy as np
from datetime import datetime
import pandas as pd

def load_h5_corr(file_path, time=None):
    """Read hdf5 file containing correlation functions for a given station pair.

    Parameters:
        file_path (str): Filename of the hdf5 file.
        time (str, optional): A given day in format `%YYYY-%mm-%dd` to extract the correlation function. By defaults (`None`), all correlation functions for the given station pair are returned.

    Returns:
        xcorr (np.ndarray): Correlation function(s). If `time` is `None`, shape is (N_days, N_lags). If `time` is given, shape is (N_lags,).
        lagtime (np.ndarray): Lag time axis corresponding to the correlation function(s).
        times (np.ndarray or datetime): Array of days corresponding to each correlation function if `time` is `None`, else a single datetime object.
        fs (float): Sampling frequency of the correlation functions.
    """

    with h5py.File(file_path, "r") as f:

        if "metadata" in f.keys():
            metadata_grp = f["metadata"]
            fs = metadata_grp["fs"][()]
            max_lag = metadata_grp["max_lag"][()]
            corr_grp = f["correlations"]
            lagtime = np.arange(-max_lag, max_lag + 1/fs, 1/fs)
            
            if time is None:
                days = sorted(corr_grp.keys())
                corr_list = [corr_grp[day][:] for day in days]
                xcorr = np.stack(corr_list, axis=0)
                times = np.array([datetime.strptime(day, "%Y-%m-%d") for day in days])
        
                full_times = pd.date_range(start=min(times), end=max(times), freq="D")
                df = pd.DataFrame(xcorr, index=times, columns=lagtime)
                df = df.reindex(index=full_times)
                xcorr = df.values.T
                times = df.index.to_pydatetime()

            else:
                xcorr = corr_grp[time][:]
                times = datetime.strptime(time, "%Y-%m-%d")
        
        else:
            xcorr = f["array"][()]
            lagtime = f["lagtime"][()]
            times = f["time"][()]
            fs = f["fs"][()]
            times = times.astype(str)
            times = np.array(times, dtype='datetime64[s]')

            full_times = pd.date_range(start=min(times), end=max(times), freq="D")
            df = pd.DataFrame(xcorr.T, index=times, columns=lagtime)
            df = df.reindex(index=full_times)
            xcorr = df.values.T
            times = df.index.to_pydatetime()
            
    return xcorr, lagtime, times, fs
