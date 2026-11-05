# Global modules
import os
import pandas as pd
from obspy import UTCDateTime

# Local modules
from sda.core.logs import add_log
import sda.core.config as conf
import sda.process.xcorr_noise.PreProcessingModules.tracesScan as Scan
from sda.process.xcorr_noise.CorrelationModules.correlationsMain02 import Correlation


def xcorr_noise(
    outputPath,
    starttime,
    endtime,
    databasePath = None,
    DataPath = None,
    Components = ["Z"], # ["Z"]
    CrossComponents = ["ZZ"], # ["ZZ"]
    stations = [],
    NumberOfProcesses = 1,
    doScan = True,
    remove_response = True,
    inventory_path = None, # Absolute path
    water_level = 60,
    response_prefilt = (0.05, 0.06, 7.0, 9.0),
    NewFrequence = 20,
    numberOfSubTrace = 12,
    freqMin = 1/10,
    freqMax = 5,
    freqmin = 0.05,
    factorTestStd = 10,
    numberOfStd = 3, # Pas utilisé si Convergence = False ?
    factorReplaceWithStd = 0,
    Convergence = False,
    ratioZero = 9.0/10.0,
    ratioE = 2,
    do1bit = None,
    factorTestStdSeisme = 2,
    divideFreq = 0.05, # Whitening : The percentage of the length of the apodization of each border in the frequency domain : Between 0 (0%) and 0.5 (50% of the window on each side, so 100%)
    lengthBorder = 100, # Not used
    HourFilter = (0, 24),
    AutoCorr = True, # Do autocorr ? [ne marche pas, laisser en True sinon tout casse !!!]
    Maxlag = 120, # [s] Maximum absolute lagitme
    LenTrace = 86400, # [s] Length of Trace
    minSubCorrKeep = 0.8,
    maxInterDistance = None,
    savePreProcessing = False,
    restricted_times = None,
    save_mode = "stack"
):
    
    """Preprocess seismic waveforms and compute ambient-noise correlations.
    Correlation functions are stored in HDF5 files at `<outputPath>/xcorr_noise/<component>/<sta1>-<sta2>.h5`.
    Waveform paths and metadata must first be indexed with `scan_data`.

    Parameters:
        outputPath (str): Project directory containing the dataset and database, and receiving
            the `xcorr_noise` results directory.
        starttime (str | UTCDateTime): UTC start, including a time of day if needed,
            e.g. `"2023-01-01"`, `"2023-01-01T06:00:00"`.
        endtime (str | UTCDateTime): UTC end, including a time of day if needed,
            e.g. `"2023-01-02"`, `"2023-01-02T00:00:00"`.
        databasePath (str | None): Existing SQLite database created by `scan_data`;
            `None` uses `<outputPath>/database.db` (default location).
        DataPath (str | None): Waveform directory supplied to preprocessing;
            `None` uses `<outputPath>/data/waveforms`.
        Components (list[str]): Waveform components to preprocess, e.g. `["Z"]`
            or `["Z", "N", "E"]`.
        CrossComponents (list[str]): Component pairs to correlate, e.g. `["ZZ"]`
            or `["ZZ", "ZN", "NZ"]`. The first letter refers to the first station.
        stations (list[str]): Station codes to include, e.g. `["ST01", "ST02"]`.
            An empty list uses all stations.
        NumberOfProcesses (int): Number of worker processes, distributed across `LenTrace`
            intervals.
        doScan (bool): Rebuild daily trace dictionaries from the existing SQLite index.
            `False` reuses `<outputPath>/xcorr_noise/DictsOfTraces`; it does not index new files.
        remove_response (bool): Remove the instrument response using StationXML metadata
            during preprocessing.
        inventory_path (str | None): Directory searched recursively for StationXML `.xml`
            files; `None` uses `<outputPath>/data/inventory`. Needed for response removal
            or an inter-station distance limit.
        water_level (float | None): Water level in dB passed to ObsPy response removal;
            `None` disables water-level stabilization. Used only with `remove_response=True`.
        response_prefilt (tuple[float, float, float, float] | None): Four response-removal
            taper corners in Hz, e.g. `(0.05, 0.06, 7.0, 9.0)`; `None` disables this pre-filter.
        NewFrequence (float): Target sampling rate in Hz after resampling, e.g. `20`.
        numberOfSubTrace (int): Number of equal sub-windows per `LenTrace` interval,
            e.g. `12` gives two-hour sub-windows for a one-day interval.
        freqMin (float): Lower frequency in Hz for spectral whitening (which also acts as a band-pass filter).
        freqMax (float): Upper frequency in Hz for spectral whitening (which also acts as a band-pass filter).
        freqmin (float): High-pass corner in Hz applied before glitch correction;
            distinct from the whitening bound `freqMin`.
        factorTestStd (float): Glitch threshold as a multiple of the trace standard
            deviation, e.g. `10` detects samples above ten standard deviations.
        numberOfStd (int): Number of glitch-correction passes when `Convergence=False`;
            the standard deviation is recalculated at each pass.
        factorReplaceWithStd (float): Replacement amplitude for glitches, as a multiple of
            the current standard deviation, preserving sign. `0` replaces them with zeros.
        Convergence (bool): Repeat glitch correction until stable, with an iteration limit.
            When `False`, perform exactly `numberOfStd` passes.
        ratioZero (float): Minimum fraction of samples with valid data (not gaps) for a sub-window to pass the coverage test; `0.9` requires 90%.
        ratioE (float): Multiplier of the interval's estimated mean sub-window energy.
            Sub-windows above this energy threshold are rejected.
        do1bit (str | None): Apply sign normalization `"before_whiten"` or
            `"after_whiten"`; `None` disables it.
        factorTestStdSeisme (float): Amplitude-clipping factor applied after whitening,
            relative to the sub-window standard deviation.
        divideFreq (float): Fraction of the whitening bandwidth tapered at each edge,
            e.g. `0.05` for 5% per edge. Use a value between `0` and `0.5`.
        lengthBorder (int): Compatibility option; currently unused by preprocessing. To be removed in a future version.
        HourFilter (tuple[float, float]): Accepted UTC hours. `(0, 24)` keeps all hours; `(22, 6)` spans midnight.
        AutoCorr (bool): Compatibility option; currently ignored. Same-station pairs
            are included regardless of this value. To be changed in a future version.
        Maxlag (float): Maximum absolute correlation lag in seconds, e.g. `120` saves
            the range from `-120` to `+120` seconds.
        LenTrace (float): Length in seconds of each consecutive, non-overlapping processing
            interval. The intervals start at `starttime`; an incomplete final interval is skipped.
        minSubCorrKeep (float): Minimum fraction of retained sub-windows for a valid stack,
            between `0` and `1`. Ignored when `save_mode="full"`.
        maxInterDistance (float | None): Maximum station-pair distance in kilometers,
            computed from the inventory. `None` applies no distance limit.
        savePreProcessing (bool): Keep the preprocessed NumPy traces after correlation;
            otherwise their temporary directories are removed.
        restricted_times (list[tuple[str, str]] | None): Allowed UTC intervals. A sub-window
            must fit entirely inside one interval, e.g.
            `[("2023-01-01T00:00:00", "2023-01-01T06:00:00")]`.
            `None` or an empty list applies no additional time restriction.
        save_mode (str): `"stack"` saves the mean of retained sub-correlations per interval;
            `"full"` saves every retained sub-correlation.

    Notes:
        - Whitening is applied only to cross-correlations; it is replaced by a band-pass
          filter for autocorrelations.

    Example:
        Compute daily vertical-component correlations after indexing the dataset:

        ```python
        from sda.process import xcorr_noise

        xcorr_noise(
            outputPath="/path/to/output",
            starttime="2023-01-01",
            endtime="2023-01-03",
            NumberOfProcesses=4,
            inventory_path="/path/to/output/data/inventory",
            remove_response=True,
            doScan=True,
            LenTrace=86400,
            numberOfSubTrace=48,
            Components=["Z"],
            CrossComponents=["ZZ"],
            stations=["ST01", "ST02"],

        )
        ```

        Save individual five-minute correlations within hourly intervals:

        ```python
        xcorr_noise(
            outputPath="/path/to/output",
            starttime="2023-01-01T00:00:00",
            endtime="2023-01-03T00:00:00",
            NumberOfProcesses=4,
            inventory_path="/path/to/output/data/inventory",
            remove_response=True,
            doScan=True,
            LenTrace=3600,
            numberOfSubTrace=12,
            Components=["Z"],
            CrossComponents=["ZZ"],
            stations=["ST01", "ST02"],
            save_mode="full",
        )
        ```
    """
    
    add_log("#"*50, level="info")
    add_log("Start process: xcorr_noise", level="info")
    
    # Prepare files
    if not os.path.isdir(outputPath):
        add_log(f"Output directory (outputPath = {outputPath}) doesn't exists. Creating the directory...", level="warning")
        os.makedirs(outputPath)

    if DataPath == None:
        DataPath = os.path.join(outputPath, "data", "waveforms")
    add_log(f"Dataset folder: {DataPath}", level="info")

    if inventory_path == None:
        inventory_path = os.path.join(outputPath, "data", "inventory")
    add_log(f"Inventory folder: {inventory_path}", level="info")

    if databasePath == None:
        databasePath = os.path.join(outputPath, "database.db")
    add_log(f"Database file: {databasePath}", level="info")
    SaveDirectory = os.path.join(outputPath, "xcorr_noise")
    add_log(f"Save correlations directory: {SaveDirectory}", level="info")
    
    # Prepare config dictionary
    config = {
        "DataPath" : DataPath,
        "databasePath" : databasePath,
        "SaveDirectory" : SaveDirectory,
        "Components" : Components,
        "CrossComponents" : CrossComponents,
        "starttime" : starttime,
        "endtime" : endtime,
        "stations" : stations,
        "NumberOfProcesses": NumberOfProcesses,
        "doScan" : doScan,
        "remove_response" : remove_response,
        "inventory_path" : inventory_path,
        "water_level" : water_level,
        "response_prefilt" : response_prefilt,
        "NewFrequence" : NewFrequence,
        "numberOfSubTrace" : numberOfSubTrace,
        "freqMin" : freqMin,
        "freqMax" : freqMax,
        "freqmin" : freqmin,
        "factorTestStd" : factorTestStd,
        "numberOfStd" : numberOfStd,
        "factorReplaceWithStd" : factorReplaceWithStd,
        "Convergence" : Convergence,
        "ratioZero" : ratioZero,
        "ratioE" : ratioE,
        "do1bit" : do1bit,
        "factorTestStdSeisme" : factorTestStdSeisme,
        "divideFreq" : divideFreq,
        "lengthBorder" : lengthBorder,
        "HourFilter" : HourFilter,
        "AutoCorr" : AutoCorr,
        "Maxlag" : Maxlag,
        "LenTrace" : LenTrace,
        "NumberSubLen" : numberOfSubTrace,
        "minSubCorrKeep" : minSubCorrKeep,
        "maxInterDistance": maxInterDistance,
        "savePreProcessing": savePreProcessing,
        "restricted_times": restricted_times,
        "save_mode": save_mode
    }
    # Convert the requested UTC interval and durations; parameter validation is deferred.
    start_ns = starttime.ns if isinstance(starttime, UTCDateTime) else pd.Timestamp(starttime).value
    end_ns = endtime.ns if isinstance(endtime, UTCDateTime) else pd.Timestamp(endtime).value
    if isinstance(endtime, str) and len(endtime) == 10:
        end_ns += 86400 * 1_000_000_000
    config["range_start_ns"] = start_ns
    config["range_end_ns"] = end_ns
    config["window_duration_ns"] = round(LenTrace * 1_000_000_000)
    config["starttime"] = UTCDateTime(ns=(start_ns // 1_000_000_000) * 1_000_000_000).strftime("%Y-%m-%d")
    config["endtime"] = UTCDateTime(ns=((end_ns - 1) // 1_000_000_000) * 1_000_000_000).strftime("%Y-%m-%d")
    config = conf.update(config)
    config["LenTrace"] = round(config["LenTrace"])
    config["Maxlag"] = round(config["Maxlag"])
    config["GoodNumber"] = config["LenTrace"] // numberOfSubTrace + config["Maxlag"]
    add_log("Configuration parameters:", level="info")
    for key in config:
        add_log(f"  - {key} : {config[key]}", level="info")
    
    # Scan step
    config["ComponentStation"] = "Z"
    Scan.treatTracesFromDirectory(config)

    # PreProcessing + Correlation step
    Correlation(config)
    
    add_log("End process: xcorr_noise", level="info")
    add_log("#"*50, level="info")
