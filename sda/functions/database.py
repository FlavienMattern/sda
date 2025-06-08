#### This file contains all the functions allowing you to create and
#### perform queries with the sqlite3 database.
#### 
#### Author : F. Mattern

####################################################
#                  MODULE IMPORTS                  #
####################################################

import os
import numpy as np
import pickle as pkl
from datetime import datetime, timedelta
import sqlite3
import geopandas as gpd
import pandas as pd
import re




####################################################
#                    FUNCTIONS                     #
####################################################

def functionRegex(value, pattern):
    c_pattern = re.compile(r"\b" + pattern.lower() + r"\b")
    return c_pattern.search(value) is not None
    

def filter(db_file, file_type=".*",
                    network=".*", station=".*", location=".*", channel=".*",
                    start="1970-01-01", end="2100-01-01"):
    
    """
    data = database_filter(db_file = "database.db",
                           file_type = "STREAM",
                           network = "FR",
                           station = "ILLK",
                           location = "00",
                           channel = "HHZ",
                           start = "2019-11-01",
                           end = "2019-11-10")
    """
    
	### Connexion à la base de données
    db = sqlite3.connect(db_file, isolation_level=None)
    
    db.create_function('REGEXP', 2, lambda x, y: 1 if re.search(x,y) else 0)
    
    ### Récupérer les portions mseed dans le range (start, end)
    # (ENDTIME >= start) & (STARTTIME <= end)
    # (   f    >= start) & (    i     <= end)
    #
    #           start                          end
    #             ├─────────────────────────────┤                   input range
    # 
    #  i       fi             fi           fi            fi     f
    #  ├───────┤├─────────────┤├───────────┤├────────────┤├─────┤    all traces
    #
    #      x    ├─────────────┤├───────────┤├────────────┤├─────┤ [1] (f >= start)
    # 
    #  ├───────┤├─────────────┤├───────────┤├────────────┤   x    [2] (i <= end)
    # 
    #      x    ├───── v ─────┤├──── v ────┤├──── v ─────┤   x       [1] & [2]
    #
    # On ajoute un jour artificiellement à end pour prendre en compte la journée entière
    end = (datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    query = """
            SELECT * FROM DATASET
            WHERE
            TYPE REGEXP '{}'
            AND
            NETWORK REGEXP '{}'
            AND
            STATION REGEXP '{}'
            AND
            LOCATION REGEXP '{}'
            AND
            CHANNEL REGEXP '{}'
            AND
            ENDTIME >= DATE('{}')
            AND
            STARTTIME <= DATE('{}')
            ;
            """.format(file_type, network, station, location, channel, start, end)

    result = pd.read_sql_query(query, db)
    
    db.close()
    
    return result