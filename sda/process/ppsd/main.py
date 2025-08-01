# Global modules
import os
import pandas as pd
from obspy import read_inventory, read
from obspy.signal import PPSD
from tqdm import tqdm
import multiprocessing
from functools import partial
import sqlite3
import warnings
warnings.filterwarnings("ignore")

# Local modules
import sda.functions.database as database
import sda.functions.jobs as jb



def save_ppsd(ppsd, folder, station):
    try:
        if ppsd is None: return
        start = min(ppsd.current_times_used).datetime.strftime("%Y-%m-%d")
        end = max(ppsd.current_times_used).datetime.strftime("%Y-%m-%d")
        filename = os.path.join(folder, f"{station}_{start}_{end}.npz")
        ppsd.save_npz(filename)
    except Exception as e:
        print(f"Error saving PPSD for {station}:\n{e}")

    
   
def init_ppsd(stream, inventory, parameters):
    ppsd = PPSD(stream[0].stats, metadata=inventory,
                ppsd_length=parameters["ppsd_length"], overlap=parameters["overlap"],
                period_smoothing_width_octaves=parameters["period_smoothing_width_octaves"],
                period_step_octaves=parameters["period_step_octaves"],
                period_limits=parameters["period_limits"],
                db_bins=parameters["db_bins"])  
    
    return ppsd
    
    

def process_ppsd_station(station, parameters, queue):
    NET, STA, LOC, CHA = station.split(".")
    inventory = parameters["inventory"]
    components = parameters["components"]
    database_path = parameters["database_path"]
    starttime = parameters["starttime"]
    endtime = parameters["endtime"]
    
    if starttime is None or endtime is None:
        db = database.filter(db_file=database_path, file_type="STREAM", station=f"^{STA}$")
    else:
        db = database.filter(db_file=database_path, file_type="STREAM", station=f"^{STA}$", start=starttime, end=endtime)
    
    db["STATION_FULLNAME"] = db["NETWORK"]+"."+db["STATION"]+"."+db["LOCATION"]+"."+db["CHANNEL"]
    db["COMPONENT"] = db["CHANNEL"].str[-1]
    db = db[db["COMPONENT"].isin(components)]
    stations = list(set(db["STATION_FULLNAME"].values))

    # Extract all files for the station
    for st in stations:
        df = db[db["STATION_FULLNAME"] == st]
        df = df.sort_values(by='STARTTIME', ascending=True)
        
        # Prepare output results
        folder = os.path.join(parameters["output_path"], "ppsd", "PPSD", st)
        os.makedirs(folder, exist_ok=True)
        files = df["FILE"]
        
        ppsd = None
        
        for idx, f in enumerate(files):           
            try:
                stream = read(f, sourcename=st)
                inventorySub = inventory.select(network=NET, station=STA, location=LOC, channel=CHA)
                stream.attach_response(inventorySub)
            except:
                continue
            
            ## Création de l'objet PPSD (header)
            if ppsd is None:
                ppsd = init_ppsd(stream, inventorySub, parameters)
            
            ## Ajout du stream au PPSD
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    ppsd.add(stream)
                    # queue.put({"JOBID":jobid, "STATUS":"DONE"})
                    ### TO DO
                    ### Sometimes, this warning is raised here :
                    ### Already covered time spans detected (e.g. %s), skipping these slices.
                    ### --> Find a way to correct it if this is not expected
                    ### Also : this message appears : IOStream.flush timed out
                    ### --> Understand and correct the associated issue
                except UserWarning as warn:
                    warn_msg = f"Warning : {warn}"
                    # Save current ppsd and create a new one
                    save_ppsd(ppsd, folder, st)
                    ppsd = init_ppsd(stream, inventorySub, parameters)
                    ppsd.add(stream)
                    # queue.put({"JOBID":jobid, "STATUS":"DONE"})
       
        if ppsd is not None:
            save_ppsd(ppsd, folder, st)


def PPSDPoolHandler(stations, parameters):
    # Define queue to update database in parallel
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    writer_process = multiprocessing.Process(target=jb.insert_job_queue, args=(queue,parameters))
    writer_process.start()
     
    # We set config dict as a non iterable argument for parallel processing
    PPSDParallelWithConfig = partial(process_ppsd_station, parameters=parameters, queue=queue)
    # Create Pool with a progress bar
    with multiprocessing.Pool(processes=parameters["n_cores"]) as p:
        with tqdm(total=len(stations), bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
            pbar.set_description("Computing PPSDs")
            for _ in p.imap_unordered(PPSDParallelWithConfig, stations):
                pbar.update()
                
    # End writting process to database
    queue.put('STOP')
    writer_process.join()
    manager.shutdown()



def ppsd(
    output_path,
    inventory_path = None,
    components = ["Z", "N", "E", "1", "2"],
    stations = None,
    starttime = None,
    endtime = None,
    n_cores = 1,
    divide_files = None, # day, month, year, None
    ppsd_length = 1800,
    overlap = 0.0,
    period_smoothing_width_octaves = 0.08,
    period_step_octaves = 0.02,
    period_limits = (1/50, 50),
    db_bins = (-200, -50, 0.25)
):
    """
    Process PPSD (Probabilistic Power Spectral Density) for seismic data.
    Parameters
    ----------
    output_path : str
        Path to the output directory where PPSD results will be saved.
    inventory_path : str, optional
        Path to the inventory files (default is None, which means no inventory will be used).
    n_cores : int, optional
        Number of CPU cores to use for parallel processing (default is 1).
    divide_files : str, optional
        If specified, files will be divided by this parameter (e.g., "day", "month", "year").
    ppsd_length : int, optional
        Length of the PPSD in seconds (default is 1800 seconds).
    overlap : float, optional
        Overlap percentage for PPSD calculation (default is 0.0).
    period_smoothing_width_octaves : float, optional
        Width of the smoothing in octaves for PPSD (default is 0.15).
    period_step_octaves : float, optional
        Step size in octaves for PPSD (default is 0.025).
    period_limits : tuple, optional
        Tuple defining the period limits for PPSD (default is (1/50, 50)).
    db_bins : tuple, optional
        Tuple defining the dB bins for PPSD (default is (-200, 20, 0.25)).
    Returns
    -------
    None
    """

    os.makedirs(output_path, exist_ok=True)
    database_path = os.path.join(output_path, "database.db")
    if inventory_path == None:
        inventory_path = os.path.join(output_path, "data", "inventory")

    print(f"[ppsd] Preparing jobs to compute ...")
    ### Initialize Job Table and fill it
    tableName = "JOBS_ppsd"
    columns   = ["JOBID", "FILE", "STATION", "STATUS"]
    jb.create_job_table(database_path, tableName, columns)

    dbFilter = database.filter(db_file=database_path, file_type="STREAM")
    files = dbFilter["FILE"]
    job_ids = dbFilter[["NETWORK", "STATION", "LOCATION", "CHANNEL", "STARTTIME", "ENDTIME"]].apply("_".join, axis=1)
    st_list = dbFilter[["NETWORK", "STATION", "LOCATION", "CHANNEL"]].apply(".".join, axis=1)
    
    
    jobs_list = []
    for idx, jobid in enumerate(job_ids):
        jobs_list.append((jobid, files[idx], st_list[idx], "TODO"))

    with sqlite3.connect(database_path) as conn:
            
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR IGNORE INTO JOBS_ppsd (JOBID, FILE, STATION, STATUS)
            VALUES (?,?,?,?);
            """, jobs_list
        )
        conn.commit()
        jobs = jb.get_jobs(conn, tableName, status="TODO") # Get all jobs in 'TODO' status
        
    # Filter jobs and stations to process
    if stations is not None:
        jobs = jobs[jobs["STATION"].apply(lambda x: x.split(".")[1]).isin(stations)]
    
    jobs = jobs[jobs["STATION"].apply(lambda x: x[-1] in components)]
    stations = list(set(jobs["STATION"].values))

    ### Create inventory object
    for path, subdirs, files in os.walk(inventory_path):
        for name in files:
            if name[-4:] == ".xml":
                invfile = os.path.join(path, name)
                inv = read_inventory(invfile, format="STATIONXML")
                try:
                    inventory.extend(inv)
                except NameError:
                    inventory = inv

    ### Run process
    parameters = {
        "n_cores": n_cores,
        "database_path": database_path,
        "output_path": output_path,
        "inventory": inventory,
        "components": components,
        "stations": stations,
        "starttime": starttime,
        "endtime": endtime,
        "ppsd_length": ppsd_length,
        "overlap": overlap,
        "period_smoothing_width_octaves": period_smoothing_width_octaves,
        "period_step_octaves": period_step_octaves,
        "period_limits": period_limits,
        "db_bins": db_bins,
        "tableName": tableName,
        "jobs": jobs
    }
    PPSDPoolHandler(stations, parameters)