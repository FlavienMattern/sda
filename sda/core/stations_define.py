import pickle as pkl
import os
import numpy as np
from itertools import product



def ReadListOfStation(config):
    if len(config['stations']) == 0:
        DictsPath = config['SaveDirectory'] + '/DictsOfTraces/'
        ListStation = []
        for file in os.listdir(DictsPath):
            with open(DictsPath+file, 'rb') as f:
                dico = pkl.load(f)
            for key in dico.keys():
                if key not in ListStation:
                    ListStation.append(key)
    else:
        ListStation = config['stations']

    return ListStation


    
def MakeCouplesOfStation(config):
    stations = ReadListOfStation(config)

    if len(stations) == 1:
        couples = [(stations[0], stations[0])]
    
    else:
        couples = list(product(stations, repeat=2))
        # Filtrer les paires qui ne sont pas dans l'ordre alphabétique et éliminer les doublons
        couples = list(set((min(pair), max(pair)) for pair in couples))

    return couples
