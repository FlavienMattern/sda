import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from obspy import read
from tqdm import tqdm

from sda.core.logs import add_log

import warnings

warnings.filterwarnings('ignore')

# Fonction pour extraire les propriétés d'un fichier
def extract_file_properties(file_path):

    try:
        stream = read(file_path, headonly=True)
    except Exception as err:
        add_log(f"Failed to read file: {file_path}\n{err}", level="error")
        return []
        
    infos = []
    NTRACE = len(stream)
    NET = stream[0].stats.network
    STA = stream[0].stats.station
    LOC = stream[0].stats.location
    CHA = stream[0].stats.channel
    fs = stream[0].stats.sampling_rate
    dt = stream[0].stats.delta
    npts = sum([stream[i].stats.npts for i in range(NTRACE)])
    calib = stream[0].stats.calib
    STARTTIME = stream[0].stats.starttime.strftime("%Y-%m-%d %H:%M:%S.%f")
    ENDTIME = stream[NTRACE-1].stats.endtime.strftime("%Y-%m-%d %H:%M:%S.%f")
    TYPE = "STREAM"
    infos.append((file_path, TYPE, NTRACE, NET, STA, LOC, CHA, fs, dt, npts, calib, STARTTIME, ENDTIME))

    return infos

# Initialisation de la base de données SQLite
def initialize_database(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DATASET (
                ID             INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                FILE           TEXT,
                TYPE           TEXT,
                NTRACE         INTEGER,
                NETWORK        TEXT,
                STATION        TEXT,
                LOCATION       TEXT,
                CHANNEL        TEXT,
                SAMPLING_RATE  REAL,
                DELTA          REAL,
                NPTS           INTEGER,
                CALIB          REAL,
                STARTTIME      TEXT,
                ENDTIME        TEXT
            )
        """)
        conn.commit()

# Fonction pour insérer en bloc des données dans la base de données
def bulk_insert(db_path, data):       
    data = [elt for sublist in data for elt in sublist]

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR IGNORE INTO DATASET (FILE, TYPE, NTRACE, NETWORK, STATION, LOCATION, CHANNEL, SAMPLING_RATE, DELTA, NPTS, CALIB, STARTTIME, ENDTIME)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);
            """, data
        )
        conn.commit()

def remove_deleted_files_from_db(db_path, existing_files):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT FILE FROM DATASET")
        db_files = {row[0] for row in cursor.fetchall()}
        files_to_remove = db_files - existing_files
        cursor.executemany("DELETE FROM DATASET WHERE FILE = ?", [(file,) for file in files_to_remove])
        conn.commit()
        
        return len(files_to_remove)
        
def added_files_in_db(db_path, existing_files):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT FILE FROM DATASET")
        db_files = {row[0] for row in cursor.fetchall()}
        files_added = existing_files - db_files
        
        return len(files_added)

def all_files_in_db(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT FILE FROM DATASET")
        db_files = {row[0] for row in cursor.fetchall()}
        
        return len(db_files)

# Fonction principale pour traiter les fichiers en parallèle
def scan_data(outputPath, dataPath=None, databasePath=None, overwrite=True, NumberOfProcesses=1, chunk_size=100):
    
    add_log("#"*50, level="info")
    add_log("Start process: scan_data", level="info")

    # Prepare files
    if not os.path.isdir(outputPath):
        add_log(f"Output directory (outputPath = {outputPath}) doesn't exists. Creating the directory...", level="warning")
        os.makedirs(outputPath)

    if dataPath == None:
        dataPath = os.path.join(outputPath, "data")
    add_log(f"Dataset directory: {dataPath}", level="info")
    if not os.path.isdir(dataPath):
        add_log(f"Dataset directory (dataPath = {dataPath}) doesn't exists.", level="error")

    if databasePath == None:
        databasePath = os.path.join(outputPath, "database.db")
    add_log(f"Database file: {databasePath}", level="info")

    
    # Regarde si la base de données est déjà existante
    folder, filename = os.path.split(databasePath)
    if (folder != "") and (not os.path.isdir(folder)):
        add_log(f"Database folder ({folder}) doesn't exists. Creating the folder...", level="warning")
        os.makedirs(folder)
    
    if overwrite:
        add_log(f"Removing existing database file: {databasePath}", level="info")
        try:
            os.remove(databasePath)
        except OSError:
            add_log(f"No existing database file to remove. Ignoring.", level="warning")
            pass
    
    # Initialiser la base de données
    add_log("Initialize database.", level="info")
    initialize_database(databasePath)

    # Lister tous les fichiers dans l'arborescence
    add_log("Listing all existing files in dataset...", level="info")
    existing_files = set()
    for dirpath, _, filenames in os.walk(dataPath):
        for filename in filenames:
            if filename.lower().endswith(('.xml',)):
                continue
            absolutePath = os.path.abspath(os.path.join(dirpath, filename))
            existing_files.add(absolutePath)
            

    # Track changes in dataset
    Nremoved = remove_deleted_files_from_db(databasePath, existing_files)
    Nadded = added_files_in_db(databasePath, existing_files)
    Nunchanged = all_files_in_db(databasePath) - Nremoved
    print(f"Track file changes : {Nadded} added | {Nremoved} removed | {Nunchanged} unchanged.")
    add_log(f"Track file changes : {Nadded} added | {Nremoved} removed | {Nunchanged} unchanged.", level="info")

    # Liste pour stocker les futures
    futures = []
    
    if Nadded == 0:
        print("No new file to add to database.")
        add_log("No new file to add to database.", level="info")
    else:
        
        add_log(f"Processing {Nadded} new files to add to database...", level="info")
        data_chunk = []
        for file_path in tqdm(existing_files, desc="Scanning dataset   "):
            result = extract_file_properties(file_path)
            if result:
                data_chunk.append(result)
                if len(data_chunk) >= chunk_size:
                    add_log(f"Inserting chunk of {len(data_chunk)} entries to database...", level="info")
                    bulk_insert(databasePath, data_chunk)
                    data_chunk = []
                    
        # Ajouter le dernier chunk
        if data_chunk:
            bulk_insert(databasePath, data_chunk)

        add_log("All files added to the database.", level="info")
        
        # with ThreadPoolExecutor(max_workers=NumberOfProcesses) as executor, tqdm(total=Nadded) as pbar:
        #     pbar.set_description("Scanning dataset   ")

        #     with sqlite3.connect(databasePath) as conn:
        #         cursor = conn.cursor()
        #         cursor.execute("SELECT FILE FROM DATASET")
        #         db_files = {row[0] for row in cursor.fetchall()}

        #     for file_path in existing_files:
        #         if file_path not in db_files:
        #             futures.append(executor.submit(extract_file_properties, file_path, merge_update))

        #     # Récupérer les résultats et les stocker en base de données par chunks
        #     data_chunk = []
        #     for future in as_completed(futures):
        #         result = future.result()
        #         if result:
        #             data_chunk.append(result)
        #             if len(data_chunk) >= chunk_size:
        #                 bulk_insert(databasePath, data_chunk)
        #                 data_chunk = []
        #         pbar.update(1)

        #     # Ajouter le dernier chunk
        #     if data_chunk:
        #         bulk_insert(databasePath, data_chunk)

    add_log("End process: scan_data", level="info")
    add_log("#"*50, level="info")

if __name__ == "__main__":
    """
    ### Exemple d'utilisation
    run(
        DataPath         = "/media/flavien/DATA/FLAVIEN/these/sample_dataset",
        DataBaseSavePath = "/media/flavien/WORK/seismo-tools/results/scan_data/database.db",
        overwrite        = True,
        chunk_size       = 10
    )
    """
    pass
