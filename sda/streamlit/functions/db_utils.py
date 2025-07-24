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
import pandas as pd
import re
import streamlit as st
import tempfile


def is_loaded():
    if "content" in st.session_state.get("database").keys():
        if st.session_state.get("database")["content"] is not None :
            return True
        return False
    return False


def get_db_infos(file):

    if file is not None:

        # st.success("Database loaded ! You can now explore the data.")
        st.session_state["database_loaded"] = True
        
        st.session_state["database"] = {
            "settings" : {
                "filename": file.name,
                "filesize": file.size,
                "wdir": "/media/flavien/Seagate Hub/alsace" # TO CHANGE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                },
            "content" : None
        }

        if file.size == 0:
            st.session_state["database"]["settings"]["filesize_str"] = file.size
        else:
            units = ["o", "ko", "Mo", "Go", "To", "Po"]
            i = 0
            while file.size >= 1024 and i < len(units) - 1:
                file.size /= 1024
                i += 1
            st.session_state["database"]["settings"]["filesize_str"] = f"{file.size:.1f} {units[i]}"

        # Créer une base SQLite temporaire (en mémoire ou fichier)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

            conn = sqlite3.connect(tmp_path)
            # cursor = conn.cursor()
            # cursor.execute("SELECT COUNT(*) FROM DATASET;")
            # count = cursor.fetchone()[0]
            # df = filter(conn) # Récupération de la base de données
            # df.set_index("ID", inplace=True)
            # st.dataframe(df, use_container_width=True)

            tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)

            dfs = {}
            for table_name in tables['name']:
                #print(f"\n📄 Lecture de la table : {table_name}")
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                dfs[table_name] = df
                # print(df.head())  # Affiche les premières lignes

            conn.close()

            st.session_state["database"]["settings"]["nfiles"] = len(df)
            st.session_state["database"]["content"] = dfs

        st.rerun()


def status_sidebar():

    if is_loaded():
        st.sidebar.success(f"✅ Database loaded !")

    else:
        st.sidebar.error("❌ Database not loaded !")


def status():

    if not is_loaded():
        st.error("❌ Database not loaded ! Please load the database in the Dashboard.")

        
    


####################################################
#                    FUNCTIONS                     #
####################################################

def functionRegex(value, pattern):
    c_pattern = re.compile(r"\b" + pattern.lower() + r"\b")
    return c_pattern.search(value) is not None
    

def filter(db, file_type=".*",
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
