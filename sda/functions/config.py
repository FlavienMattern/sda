import importlib.util
from sda.functions.date_utils import get_day
import os
import pickle


def save(config, savepath):
    try:
        os.makedirs(savepath)
    except:
        pass
    filename = os.path.join(savepath, "config.pkl")
    with open(filename, 'wb') as f:
        pickle.dump(config, f)



def load(filename):
    with open(filename, 'rb') as f:
        config = pickle.load(f)
    return config



def update(config):
    
    if "LenTrace" in config:
        config['LenTrace'] = config['LenTrace'] * config['NewFrequence']
    
    if "starttime" in config:
        FirstYear, FirstDay = get_day(config["starttime"])
        config['FirstYear'] = FirstYear
        config['FirstDay'] = FirstDay
    
    if "endtime" in config:
        LastYear, LastDay = get_day(config["endtime"])
        config['LastYear'] = LastYear
        config['LastDay'] = LastDay
    
    if "DataPath" in config:
        DataPath = config["DataPath"]
        if DataPath[-1] == os.sep : DataPath = DataPath[:-1]
        config['DataPath'] = DataPath
        
    if "SaveDirectory" in config:    
        SaveDirectory = config["SaveDirectory"]
        if SaveDirectory[-1] == os.sep : SaveDirectory = SaveDirectory[:-1]
        SaveDirectory = os.path.join(SaveDirectory, 'EXP')
        config['SaveDirectory'] = SaveDirectory
    
    if ("Maxlag" in config) and ("NewFrequence" in config):    
        Maxlag = config["Maxlag"] * config["NewFrequence"] # In nb of points
        config['Maxlag'] = Maxlag
        
    if ("LenTrace" in config) and ("NumberSubLen" in config):
        # GoodNumber = int(config["LenTrace"] / config["NumberSubLen"] * 1.2)
        # GoodNumber must have the size of the SubWindow where correlation are computed, plus the length of the correlation (MaxLag)
        GoodNumber = int(config["LenTrace"] / config["NumberSubLen"] + Maxlag)
        config['GoodNumber'] = GoodNumber
    
    if "doScan" in config:
        if config["doScan"]:
            HasToMakeDictOfTraces = True
        else:
            HasToMakeDictOfTraces = False
        config['HasToMakeDictOfTraces'] = HasToMakeDictOfTraces

    return config
