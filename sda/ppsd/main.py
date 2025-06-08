# Define local modules path
import sys; sys.path.insert(0, "../")

# Global modules
import os
from obspy import read_inventory, read
from obspy.signal import PPSD
from tqdm import tqdm
import multiprocessing
from functools import partial
import sqlite3
import warnings
warnings.filterwarnings("error")

# Local modules
import sda.functions.database as database
import sda.functions.jobs as jb


def save_ppsd(ppsd, folder, station):
    start = min(ppsd.current_times_used).datetime.strftime("%Y-%m-%d")
    end = max(ppsd.current_times_used).datetime.strftime("%Y-%m-%d")
    filename = os.path.join(folder, f"{station}_{start}_{end}.npz")
    ppsd.save_npz(filename)   
    
    
   
def initialize_ppsd(stream, inventory, parameters):
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
    jobs = parameters["jobs"]

    # Extract all files for the station
    jobsFilter = jobs.loc[jobs["STATION"] == station].sort_values(by="JOBID")
    job_ids = jobsFilter["JOBID"]
    
    # Prepare output results
    folder = os.path.join(parameters["outputPath"], "ppsd", station)
    if not os.path.isdir(folder): os.makedirs(folder)
    
    for idx, jobid in enumerate(job_ids):
        f = jobsFilter.loc[jobsFilter["JOBID"] == jobid]["FILE"].values[0]
        
        stream = read(f, sourcename=station)
        inventorySub = inventory.select(network=NET, station=STA, location=LOC, channel=CHA)
        stream.attach_response(inventorySub)
        
        ## Création de l'objet PPSD (header)
        if idx == 0:
            ppsd = initialize_ppsd(stream, inventorySub, parameters)
        
        ## Ajout du stream au PPSD
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                ppsd.add(stream)
                queue.put({"JOBID":jobid, "STATUS":"DONE", "COMMENT":""})
                ### TO DO
                ### Sometimes, this warning is raised here :
                ### Already covered time spans detected (e.g. %s), skipping these slices.
                ### --> Find a way to correct it if this is not expected
                ### Also : this message appears : IOStream.flush timed out
                ### --> Understand and correct the associated issue
            except UserWarning as warn:
                warn_msg = f"Warning : {warn}"
                if "sampling rate" in warn_msg:
                    # Save current ppsd and create a new one
                    save_ppsd(ppsd, folder, station)
                    ppsd = initialize_ppsd(stream, inventorySub, parameters)
                    ppsd.add(stream)
                    queue.put({"JOBID":jobid, "STATUS":"DONE", "COMMENT":""})
                else:
                    queue.put({"JOBID":jobid, "STATUS":"DONE", "COMMENT":f"{warn_msg}"})
                

    save_ppsd(ppsd, folder, station)
    
    
    
def PPSDPoolHandler(stations, parameters):  
    # Define queue to update database in parallel
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    writer_process = multiprocessing.Process(target=jb.insert_job_queue, args=(queue,parameters))
    writer_process.start()
     
    # We set config dict as a non iterable argument for parallel processing
    PPSDParallelWithConfig = partial(process_ppsd_station, parameters=parameters, queue=queue)
    # Create Pool with a progress bar
    with multiprocessing.Pool(processes=parameters["Ncores"]) as p:
        with tqdm(total=len(stations)) as pbar:
            pbar.set_description("PPSD   ")
            for _ in p.imap_unordered(PPSDParallelWithConfig, stations):
                pbar.update()
                
    # End writting process to database
    queue.put('STOP')
    writer_process.join()
    manager.shutdown()



def run(
    outputPath,
    databasePath=None,
    inventoryPath=None,
    NumberOfProcesses=1,
    ppsd_length = 1800,
    overlap = 0.0,
    period_smoothing_width_octaves = 0.15,
    period_step_octaves = 0.025,
    period_limits = (1/50, 30),
    db_bins = (-200, 20, 0.25)
):

    if not os.path.isdir(outputPath): os.makedirs(outputPath)
    if databasePath == None:
        databasePath = os.path.join(outputPath, "database.db")
    if inventoryPath == None:
        inventoryPath = os.path.join(outputPath, "data", "inventory")

    ### Initialiez Job Table and fill it
    tableName = "JOBS_ppsd"
    columns   = ["JOBID", "FILE", "STATION", "STATUS", "COMMENT"]
    jb.create_job_table(databasePath, tableName, columns)

    dbFilter = database.filter(db_file=databasePath, file_type="STREAM")
    files = dbFilter["FILE"]
    job_ids = dbFilter[["NETWORK", "STATION", "LOCATION", "CHANNEL", "STARTTIME", "ENDTIME"]].apply("_".join, axis=1)
    stations = dbFilter[["NETWORK", "STATION", "LOCATION", "CHANNEL"]].apply(".".join, axis=1)

    with sqlite3.connect(databasePath) as connection:
        
        for idx, jobid in enumerate(job_ids):
            jb.insert_job(connection, tableName, (jobid, files[idx], stations[idx], "TODO", ""))

        # Get all jobs in 'TODO' status
        jobs = jb.get_jobs(connection, tableName, status="TODO")
        stations = list(set(list(jobs["STATION"].values)))
    
    ### Create inventory object
    for path, subdirs, files in os.walk(inventoryPath):
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
        "Ncores": NumberOfProcesses,
        "databasePath": databasePath,
        "outputPath": outputPath,
        "inventory": inventory,
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