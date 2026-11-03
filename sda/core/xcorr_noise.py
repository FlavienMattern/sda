import h5py
import numpy as np
import pandas as pd
from obspy import UTCDateTime


def load_h5_corr(file_path, time=None):
    """Read hdf5 file containing correlation functions for a given station pair.

    Parameters:
        file_path (str): Filename of the hdf5 file.
        time (str, optional): UTC start time of the correlation to extract. By default (None), all correlations are returned.

    Returns:
        xcorr (np.ndarray): Correlation function(s), with shape (N_lags, N_times), or (N_lags,) if time is given.
        lagtime (np.ndarray): Lag time axis corresponding to the correlation function(s).
        times (np.ndarray or datetime): Start times of the correlations, or a single timestamp if time is given.
        metadata (dict): fs, max_lag, save_mode, times_stack, n_retained and n_subwindows. Counts are unavailable for postprocessing files.
    """
    with h5py.File(file_path, "r") as f:
        # The active postprocessing writer stores its matrix at the file root.
        if "array" in f:
            xcorr = f["array"][:]
            lagtime = f["lagtime"][:]
            starts = f["time"][:]
            metadata = dict(fs=float(f["fs"][()]), max_lag=float(np.max(np.abs(lagtime))),
                            save_mode="stack", times_stack=starts.astype("datetime64[ns]"),
                            n_retained=None, n_subwindows=None)
        else:
            metadata = dict(f["metadata"].attrs)
            metadata["n_subwindows"] = int(metadata["n_subwindows"])
            fs, max_lag = metadata["fs"], metadata["max_lag"]
            lag_samples = round(max_lag * fs)
            lagtime = np.arange(-lag_samples, lag_samples + 1) / fs
            correlations = f["correlations"]
            keys = sorted(correlations, key=int)
            records = [correlations[key] for key in keys]
            starts = np.asarray(keys, dtype="int64")
            metadata["times_stack"] = starts.astype("datetime64[ns]")
            metadata["n_retained"] = np.asarray([record.attrs["n_retained"] for record in records], dtype=int)
            if metadata["save_mode"] == "stack":
                xcorr = np.column_stack([record["data"][:] for record in records])
            else:
                xcorr = np.concatenate([record["data"][:] for record in records], axis=0).T
                starts = np.concatenate([record["times"][:] for record in records])

        times = starts.astype("datetime64[ns]")
        day_ns = 86400 * 1_000_000_000
        if metadata["save_mode"] == "stack" and np.all(starts % day_ns == 0):
            times = pd.to_datetime(starts).to_pydatetime()
        if time is not None:
            target = time.ns if isinstance(time, UTCDateTime) else pd.Timestamp(time).value
            indices = np.flatnonzero(starts == target)
            if not len(indices):
                raise KeyError(f"No correlation starts at {time}.")
            index = int(indices[0])
            xcorr, times = xcorr[:, index], times[index]
        return xcorr, lagtime, times, metadata
