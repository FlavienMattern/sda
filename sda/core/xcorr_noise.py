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
        metadata (dict): Sampling frequency (fs), maximum lag and, when available, window bounds, retained counts, selection masks and input data coverage.
    """
    with h5py.File(file_path, "r") as f:
        # The active postprocessing writer stores its matrix at the file root.
        if "array" in f:
            xcorr = f["array"][:]
            lagtime = f["lagtime"][:]
            times = pd.to_datetime(f["time"][:].astype(str))
            frame = pd.DataFrame(xcorr.T, index=times, columns=lagtime)
            frame = frame.reindex(pd.date_range(times.min(), times.max(), freq="D"))
            metadata = dict(fs=float(f["fs"][()]), max_lag=float(np.max(np.abs(lagtime))),
                            save_mode="stack", n_retained=None, n_total=None)
            if time is not None:
                target = pd.Timestamp(time.ns, unit="ns") if isinstance(time, UTCDateTime) else pd.Timestamp(time)
                return frame.loc[target].values, lagtime, target.to_pydatetime(), metadata
            return frame.values.T, lagtime, frame.index.to_pydatetime(), metadata

        meta, correlations = f["metadata"], f["correlations"]
        fs = float(meta["fs"][()])
        max_lag = float(meta["max_lag"][()])
        lag_samples = round(max_lag * fs)
        lagtime = np.arange(-lag_samples, lag_samples + 1) / fs
        windows = meta["windows"]
        keys = sorted(windows, key=lambda key: windows[key].attrs["start_ns"])
        records = [windows[key] for key in keys]
        bounds = {name: np.asarray([record.attrs[name] for record in records], dtype="int64")
                  for name in ("start_ns", "end_ns", "n_retained", "n_total")}
        for name in ("retained", "data_coverage"):
            values = [record[name][:] for record in records]
            bounds[name] = np.stack(values) if values and len({value.shape for value in values}) == 1 else values
        bounds["row_count"] = np.asarray([
            (1 if correlations[key].ndim == 1 else len(correlations[key])) if key in correlations else 0
            for key in keys
        ])
        modes = {record.attrs["save_mode"] for record in records}
        mode = next(iter(modes)) if len(modes) == 1 else "mixed"
        metadata = dict(save_mode=mode, fs=fs, max_lag=max_lag, windows=bounds,
                        n_retained=bounds["n_retained"], n_total=bounds["n_total"])

        data, starts, ends = [], [], []
        for key, record in zip(keys, records):
            if key not in correlations:
                continue
            values = correlations[key][:]
            start, end = int(record.attrs["start_ns"]), int(record.attrs["end_ns"])
            total = int(record.attrs["n_total"])
            if values.ndim == 1:
                data.append(values[None, :])
                starts.append(start)
                ends.append(end)
            else:
                data.append(values)
                indices = np.flatnonzero(record["retained"][:])
                starts.extend(start + (int(i) * (end - start) + total // 2) // total for i in indices)
                ends.extend(start + ((int(i) + 1) * (end - start) + total // 2) // total for i in indices)
        xcorr = np.concatenate(data, axis=0).T if data else np.empty((len(lagtime), 0), dtype="float32")
        starts, ends = np.asarray(starts, dtype="int64"), np.asarray(ends, dtype="int64")
        order = np.argsort(starts)
        starts, ends, xcorr = starts[order], ends[order], xcorr[:, order]
        durations = bounds["end_ns"] - bounds["start_ns"]
        if mode == "stack" and len(durations) and np.all(durations == durations[0]):
            duration = int(durations[0])
            grid = np.arange(bounds["start_ns"][0], bounds["start_ns"][-1] + duration, duration, dtype="int64")
            aligned = np.full((len(lagtime), len(grid)), np.nan, dtype="float32")
            aligned[:, (starts - grid[0]) // duration] = xcorr
            starts, ends, xcorr = grid, grid + duration, aligned
        if time is not None:
            target = time.ns if isinstance(time, UTCDateTime) else pd.Timestamp(time).value
            indices = np.flatnonzero(starts == target)
            if not len(indices):
                raise KeyError(f"No correlation starts at {time}.")
            index = int(indices[0])
            starts, ends, xcorr = starts[index:index + 1], ends[index:index + 1], xcorr[:, index]
        metadata["start_ns"], metadata["end_ns"] = starts, ends
        times = starts.astype("datetime64[ns]")
        day_ns = 86400 * 1_000_000_000
        if mode == "stack" and len(durations) and np.all(durations == day_ns) and np.all(starts % day_ns == 0):
            times = pd.to_datetime(starts).to_pydatetime()
        if time is not None:
            times = times[0]
        return xcorr, lagtime, times, metadata
