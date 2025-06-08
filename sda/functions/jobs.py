# Define local modules path
import sys; sys.path.insert(0, "../")

# Global modules
import sqlite3
import pandas as pd

# Local modules
import sda.functions.database as database


# Initialisation de la table de jobs
def create_job_table(databasePath, tableName, columns):
    
    content = f"""
        CREATE TABLE IF NOT EXISTS {tableName} (
            ID  INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            {''.join([f'{elt} TEXT,' if (idx!=len(columns)-1) else f'{elt} TEXT' for idx, elt in enumerate(columns)])}
        )
    """
    
    with sqlite3.connect(databasePath) as conn:
        cursor = conn.cursor()
        cursor.execute(content)
        conn.commit()
        
        
        
def insert_job(connection, tableName, row):
    
    if not check_jobid_exists(connection, tableName, row[0]):
        cursor = connection.execute(f"select * from {tableName}")
        columns = list(map(lambda x: x[0], cursor.description))[1:]
        
        connection.execute(f"""
            INSERT OR IGNORE INTO {tableName} ({",".join(columns)})
            VALUES ({''.join([f"'{elt}'," if (idx!=len(row)-1) else f"'{elt}'" for idx, elt in enumerate(row)])});
            """
        )
        
        
        
def insert_job_queue(queue, parameters):
    databasePath = parameters["databasePath"]
    tableName = parameters["tableName"]
    
    connection = sqlite3.connect(databasePath)
    cursor = connection.cursor()
    
    while True:
        record = queue.get()
        if record == 'STOP':
            break
        query = f"""
                UPDATE {tableName}
                SET
                    STATUS = '{record["STATUS"]}',
                    COMMENT = '{record["COMMENT"]}'
                WHERE JOBID = '{record["JOBID"]}';
            """
        # print(query)
        cursor.execute(query)
        connection.commit()
    connection.close()
        
        
        
def update_status(databasePath, tableName, jobid, status, comment=""):
    with sqlite3.connect(databasePath) as connection:
        connection.execute(f"""
                UPDATE {tableName}
                SET
                    STATUS = '{status}',
                    COMMENT = '{comment}',
                WHERE JOBID = '{jobid}';
            """
        )
        
     
     
def check_jobid_exists(connection, tableName, job_id):
    query = f"""
        SELECT * FROM {tableName}
        WHERE
        JOBID == '{job_id}'
        ;
        """
    result = pd.read_sql_query(query, connection)
    return len(result) > 0



def get_jobs(connection, tableName, status):
    query = f"""
        SELECT * FROM {tableName}
        WHERE
        STATUS == '{status}'
        ;
        """
    result = pd.read_sql_query(query, connection)
    return result
    


# ####################################################################################        
# # MAIN PROGRAM (to put where we need to create a job table)
# databasePath = "/media/flavien/WORK/seismo-tools/results/test/database.db"
# outputPath   = "/media/flavien/WORK/seismo-tools/results/test"
# tableName    = "JOBS_ppsd"

# # Initialiez Job Table and fill it
# columns      = ["JOBID", "FILE", "STATION", "STATUS", "COMMENT"]
# create_job_table(databasePath, tableName, columns)

# dbFilter = database.filter(db_file=databasePath, file_type="STREAM")
# files = dbFilter["FILE"]
# job_ids = dbFilter[["NETWORK", "STATION", "LOCATION", "CHANNEL", "STARTTIME", "ENDTIME"]].apply("_".join, axis=1)
# stations = dbFilter[["NETWORK", "STATION", "LOCATION", "CHANNEL"]].apply(".".join, axis=1)

# with sqlite3.connect(databasePath) as connection:
#     for idx, jobid in enumerate(job_ids):
#         insert_job(connection, tableName, (jobid, files[idx], stations[idx], "TODO", ""))

#     # Make process
#     jobs = get_jobs(connection, tableName, status="TODO")
#     stations = list(set(list(jobs["STATION"].values)))

# for station in stations[:2]:
#     jobsFilter = jobs.loc[jobs["STATION"] == station].sort_values(by="JOBID")
    
#     job_ids = jobsFilter["JOBID"]
#     # files = jobsFilter["FILE"]
#     # files = list(dict.fromkeys(files)) # Remove duplicates by keeping list order
    
#     for idx, jobid in enumerate(job_ids):
#         f = jobsFilter.loc[jobsFilter["JOBID"] == jobid]["FILE"].values[0]
#         print(f)
        
#         #### 
#         # DO SOME PROCESSING
#         ####
        
#         # Update job status
#         update_status(databasePath, tableName, jobid, status="DONE")