import os, re, math, sqlite3
import pandas as pd
from datetime import datetime, timedelta



def convert_size(size_bytes):
    if size_bytes == 0:
        return "0 octet"
    size_name = ("o", "Ko", "Mo", "Go", "To", "Po", "Eo", "Zo", "Yo")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"




def functionRegex(value, pattern):
        c_pattern = re.compile(r"\b" + pattern.lower() + r"\b")
        return c_pattern.search(value) is not None



class Database:

    def __init__(self, database_file):
        self.database_full_filename   = os.path.abspath(database_file)
        self.database_filename        = os.path.basename(self.database_full_filename)
        self.database_folderpath      = os.path.dirname(database_file)
        self.database_file_size       = os.path.getsize(database_file)

        conn = sqlite3.connect(self.database_full_filename)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM DATASET")
        self.database_nlines = cursor.fetchone()[0]
        conn.commit()
        conn.close()



    def __repr__(self):
        conn = sqlite3.connect(self.database_full_filename)
        df = pd.read_sql_query("SELECT * FROM DATASET LIMIT 10", conn)

        text  = f"[{self.database_filename}]    "
        text += f"{convert_size(self.database_file_size)}  |  "
        text += f"{self.database_nlines} rows\n"
        text += f" └ {self.database_full_filename }"
        text += "\n\nFirst 10 rows of database :\n\n"
        text += str(df)

        return text



    def __str__(self):
        return self.__repr__()
    


    def change_datapath(self, source, destination):
        """
        Change the pattern 'source' by 'destination' for all stream paths in the database.
        """

        conn = sqlite3.connect(self.database_full_filename)
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE DATASET
            SET FILE = REPLACE(FILE, ?, ?)
        """, (source, destination))

        conn.commit()
        conn.close()

        print("Filepath has been changed in the database !")
        print(f"{source} -> {destination}")



    def filter(self, file_type=".*",
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
        db = sqlite3.connect(self.database_full_filename, isolation_level=None)
        
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
