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
    SaveSubLen = False,
    AutoCorr = True, # Do autocorr ? [ne marche pas, laisser en True sinon tout casse !!!]
    Maxlag = 120, # [s] Maximum absolute lagitme
    LenTrace = 86400, # [s] Length of Trace
    # NumberSubLen = 12, # A enlever et à mettre égal à numberOfSubTrace dans le config dict en dessous (cf paramètre commenté l.96) !!!!!!!!!!!!!!!!!!!!!!!
    minSubCorrKeep = 0.8,
    maxInterDistance = None,
    savePreProcessing = False,
    restricted_times = None,
    save_mode = "stack"
):
    
    """
    Performs cross-correlation noise processing on seismic data. This function prepares and processes seismic waveform data for cross-correlation analysis, including optional preprocessing steps such as instrument response removal, frequency filtering, and data whitening. It supports parallel processing and various configuration options for customizing the cross-correlation workflow.

    Parameters:
        outputPath (str): Path to the directory where output files will be saved.
        starttime (datetime or str): UTC start, including an optional time of day.
        endtime (datetime or str): Exclusive UTC end. A date-only string includes that entire day.
        databasePath (str, optional): Path to the database file. Defaults to None.
        DataPath (str, optional): Path to the waveform data. Defaults to None.
        Components (list of str, optional): List of components to process (e.g., ["Z"]). Defaults to ["Z"].
        CrossComponents (list of str, optional): List of cross-components for correlation (e.g., ["ZZ"]). Defaults to ["ZZ"].
        stations (list, optional): List of station identifiers to include. Defaults to [] (all stations).
        NumberOfProcesses (int, optional): Number of parallel processes to use. Defaults to 1.
        doScan (bool, optional): Whether to scan and index available data. Defaults to True.
        remove_response (bool, optional): Whether to remove instrument response. Defaults to True.
        inventory_path (str, optional): Path to the station inventory file. Defaults to None.
        water_level (float, optional): Water level for response removal. Defaults to 60.
        response_prefilt (tuple, optional): Frequency pre-filter for response removal. Defaults to (0.05, 0.06, 7.0, 9.0).
        NewFrequence (float, optional): Target sampling frequency after resampling. Defaults to 20.
        numberOfSubTrace (int, optional): Number of sub-traces per trace for correlation. Defaults to 12.
        freqMin (float, optional): Minimum frequency for filtering. Defaults to 1/10.
        freqMax (float, optional): Maximum frequency for filtering. Defaults to 5.
        freqmin (float, optional): Alternative minimum frequency for filtering. Defaults to 0.05.
        factorTestStd (float, optional): Factor for standard deviation test. Defaults to 10.
        numberOfStd (int, optional): Number of standard deviations for outlier detection. Defaults to 3.
        factorReplaceWithStd (float, optional): Factor for replacing outliers with standard deviation. Defaults to 0.
        Convergence (bool, optional): Whether to use convergence criteria. Defaults to False.
        ratioZero (float, optional): Ratio threshold for zero values. Defaults to 0.9.
        ratioE (float, optional): Ratio threshold for event detection. Defaults to 2.
        do1bit (bool, optional): Whether to apply 1-bit normalization. Defaults to None.
        factorTestStdSeisme (float, optional): Factor for seismic standard deviation test. Defaults to 2.
        divideFreq (float, optional): Percentage for frequency domain apodization (0 to 0.5). Defaults to 0.05.
        lengthBorder (int, optional): Length of border for apodization (not used). Defaults to 100.
        HourFilter (tuple, optional): Tuple specifying the hour range for filtering (start, end). Defaults to (0, 24).
        SaveSubLen (bool, optional): Legacy export of retained sub-correlations to separate NumPy files. Defaults to False. Use save_mode to choose the HDF5 output.
        AutoCorr (bool, optional): Whether to compute autocorrelation (must be True). Defaults to True.
        Maxlag (int, optional): Maximum absolute lag time in seconds. Defaults to 120.
        LenTrace (float, optional): Duration in seconds of consecutive, non-overlapping correlation intervals. Defaults to 86400. Incomplete final intervals are skipped.
        minSubCorrKeep (float, optional): Minimum fraction of retained sub-windows required to save a stack. Defaults to 0.8. Full mode saves every retained sub-correlation.
        maxInterDistance (float, optional): Maximum inter-station distance for correlation. Defaults to None.
        savePreProcessing (bool, optional): Whether to save preprocessed data. Defaults to False.
        restricted_times (list or None, optional): List of restricted time intervals. Defaults to None.
        save_mode (str, optional): "stack" (default) saves a stack over LenTrace; "full" saves every retained sub-correlation. Both modes record retained counts. SaveSubLen remains the separate legacy NumPy export option.

    Returns:
        None

    Notes:
        - This function is intended for batch processing of seismic noise cross-correlation.
        - Some parameters are not currently used but are included for compatibility or future use.
        - The function assumes that required directories and files exist or will be created as needed.

    Example:
        ```python
        xcorr_noise(
            outputPath="/path/to/output",
            starttime="2023-01-01T00:00:00",
            endtime="2023-01-02T00:00:00",
            databasePath="/path/to/database.db",
            DataPath="/path/to/data",
            Components=["Z"],
            CrossComponents=["ZZ"],
            stations=["ST01", "ST02"],
            NumberOfProcesses=4,
            doScan=True,
            remove_response=True,
            inventory_path="/path/to/inventory.xml"
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
        "SaveSubLen" : SaveSubLen,
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
