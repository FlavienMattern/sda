import os
import math
import sqlite3
import pandas as pd



def convert_size(size_bytes):
    if size_bytes == 0:
        return "0 octet"
    size_name = ("o", "Ko", "Mo", "Go", "To", "Po", "Eo", "Zo", "Yo")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"



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
