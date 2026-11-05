import os
import numpy as np
import pickle as pkl
import geopandas as gpd
import pandas as pd
from obspy.signal import PPSD
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")



def get_ppsd(station_name, ppsd_path):
    ppsd_folder = os.path.join(ppsd_path, station_name)
    ppsd = None

    for file in os.listdir(ppsd_folder):
        filename = os.path.join(ppsd_folder, file)
        if ppsd is None:
            try:
                ppsd = PPSD.load_npz(filename, allow_pickle=True)
            except:
                continue
        else:
            ppsd.add_npz(filename, allow_pickle=True)

    ppsd_array = ppsd.current_histogram.T / ppsd.current_histogram_count * 100
    ppsd_periods = ppsd.period_bin_centers
    ppsd_amplitudes = ppsd.db_bin_centers

    return ppsd_periods, ppsd_amplitudes, ppsd_array, ppsd



def get_spectrogram(ppsd, time_sampling=None):
    ppsd_spec = np.array(ppsd.psd_values).T
    ppsd_times = np.array(ppsd.times_processed)
    ppsd_periods = ppsd.period_bin_centers

    ppsd_times = pd.to_datetime([t.datetime for t in ppsd_times])

    if time_sampling is not None:
        df = pd.DataFrame(ppsd_spec.T, index=ppsd_times, columns=ppsd_periods)
        df_resampled = df.resample(time_sampling).median()
        ppsd_spec = df_resampled.to_numpy().T
        ppsd_times = df_resampled.index

    return ppsd_times, ppsd_periods, ppsd_spec



def get_timeseries(ppsd, fmin, fmax, time_sampling=None):
    ppsd_spec = np.array(ppsd.psd_values).T
    ppsd_times = np.array(ppsd.times_processed)
    ppsd_periods = ppsd.period_bin_centers

    ppsd_times = pd.to_datetime([t.datetime for t in ppsd_times])

    if time_sampling is not None:
        df = pd.DataFrame(ppsd_spec.T, index=ppsd_times, columns=ppsd_periods)
        df_resampled = df.resample(time_sampling).median()
        # df_resampled = df_resampled.asfreq(time_sampling)
        ppsd_spec = df_resampled.to_numpy().T
        ppsd_times = df_resampled.index

    f = 1/ppsd_periods
    freq_mask = np.where((f >= fmin) & (f <= fmax))
    ts = np.nanmedian(ppsd_spec[freq_mask], axis=0)
    ts[ts<-200] = np.nan
    ts[ts>0] = np.nan

    return ppsd_times, ts



def get_values(ppsd, freqs, times):
    ppsd_spec = np.array(ppsd.psd_values).T
    ppsd_times = np.array(ppsd.times_processed)
    ppsd_periods = ppsd.period_bin_centers
    ppsd_times = pd.to_datetime([t.datetime for t in ppsd_times])
    f = 1/ppsd_periods

    results = {}
    for (fmin, fmax) in freqs:
        freq_str = f"{fmin:.3f}-{fmax:.3f} Hz"

        if freq_str not in results:
                results[freq_str] = {}

        for (tmin, tmax) in times:
            freq_mask = np.where((f >= fmin) & (f <= fmax))
            time_mask = (ppsd_times >= tmin) & (ppsd_times <= tmax)
            value = float(np.nanmedian(ppsd_spec[freq_mask][:, time_mask]))
            time_str = f"{tmin.strftime('%Y-%m-%d_%H:%M:%S')}"

            results[freq_str][time_str] = value

    return results



def get_all_values(stations_list, ppsd_path, filename, freqs, times, inventory):

    results = {}
    for (fmin, fmax) in freqs:
        freq_str = f"{fmin:.3f}-{fmax:.3f} Hz"
        if freq_str not in results:
                results[freq_str] = {}
        for (tmin, tmax) in times:
            time_str = f"{tmin.strftime('%Y-%m-%d_%H:%M:%S')}"
            results[freq_str][time_str] = gpd.GeoDataFrame(columns=["station", "noise_level", "geometry"], geometry="geometry", crs=inventory.crs)

    for station_name in tqdm(stations_list, desc="Extracting data"):
        station_code = ".".join(station_name.split(".")[:2])
        _, _, _, ppsd = get_ppsd(station_name, ppsd_path)
        sta_data = get_values(ppsd, freqs, times)

        for (fmin, fmax) in freqs:
            freq_str = f"{fmin:.3f}-{fmax:.3f} Hz"

            # Remove mean values
            mean_value = np.nanmean(list(sta_data[freq_str].values()))
            sta_data[freq_str] = {
                date: float(value - mean_value)
                for date, value in sta_data[freq_str].items()
            }

            for (tmin, tmax) in times:
                try:
                    time_str = f"{tmin.strftime('%Y-%m-%d_%H:%M:%S')}"
                    noise_level = sta_data[freq_str][time_str]
                    geom = inventory.loc[inventory["station_name"] == station_code, "geometry"].iloc[0]
                    df = gpd.GeoDataFrame({"station": [station_name],"noise_level": [noise_level]}, geometry=[geom], crs=inventory.crs)
                    results[freq_str][time_str] = pd.concat([results[freq_str][time_str], df], ignore_index=True)
                except:
                    continue

    with open(filename, "wb") as f:
        pkl.dump(results, f)

    return results