# Global modules
import os

# Local modules
# import sda.functions.config as conf
# import sda.xcorr_noise.PreProcessingModules.tracesScan as Scan
# from sda.xcorr_noise.CorrelationModules.correlationsMain02 import Correlation


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
    restricted_times = None
):
    
    print("xcorr_noise: Starting cross-correlation noise processing...")
    
    # # Prepare files
    # if not os.path.isdir(outputPath): os.makedirs(outputPath)
    # if DataPath == None:
    #     DataPath = os.path.join(outputPath, "data", "waveforms")
    # if inventory_path == None:
    #     inventory_path = os.path.join(outputPath, "data", "inventory")
    # if databasePath == None:
    #     databasePath = os.path.join(outputPath, "database.db")
    # SaveDirectory = os.path.join(outputPath, "xcorr_noise")
    
    # # Prepare config dictionary
    # config = {
    #     "DataPath" : DataPath,
    #     "databasePath" : databasePath,
    #     "SaveDirectory" : SaveDirectory,
    #     "Components" : Components,
    #     "CrossComponents" : CrossComponents,
    #     "starttime" : starttime,
    #     "endtime" : endtime,
    #     "stations" : stations,
    #     "NumberOfProcesses": NumberOfProcesses,
    #     "doScan" : doScan,
    #     "remove_response" : remove_response,
    #     "inventory_path" : inventory_path,
    #     "water_level" : water_level,
    #     "response_prefilt" : response_prefilt,
    #     "NewFrequence" : NewFrequence,
    #     "numberOfSubTrace" : numberOfSubTrace,
    #     "freqMin" : freqMin,
    #     "freqMax" : freqMax,
    #     "freqmin" : freqmin,
    #     "factorTestStd" : factorTestStd,
    #     "numberOfStd" : numberOfStd,
    #     "factorReplaceWithStd" : factorReplaceWithStd,
    #     "Convergence" : Convergence,
    #     "ratioZero" : ratioZero,
    #     "ratioE" : ratioE,
    #     "do1bit" : do1bit,
    #     "factorTestStdSeisme" : factorTestStdSeisme,
    #     "divideFreq" : divideFreq,
    #     "lengthBorder" : lengthBorder,
    #     "HourFilter" : HourFilter,
    #     "SaveSubLen" : SaveSubLen,
    #     "AutoCorr" : AutoCorr,
    #     "Maxlag" : Maxlag,
    #     "LenTrace" : LenTrace,
    #     "NumberSubLen" : numberOfSubTrace,
    #     "minSubCorrKeep" : minSubCorrKeep,
    #     "maxInterDistance": maxInterDistance,
    #     "savePreProcessing": savePreProcessing,
    #     "restricted_times": restricted_times
    # }
    # config = conf.update(config)
    
    # # Scan step
    # config["ComponentStation"] = "Z"
    # Scan.treatTracesFromDirectory(config)

    # # PreProcessing + Correlation step
    # Correlation(config)