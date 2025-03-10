"""
This file is to read the CSV and load the data into database
"""

import sqlite3
import pandas as pd

# Load movies into the database
def load_movies_into_db(csv_file="movies.csv"):
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            year INTEGER NOT NULL,
            genres TEXT NOT NULL,
            directors TEXT NOT NULL,
            cast TEXT NOT NULL,
            rating REAL NOT NULL,
            synopsis TEXT
        )
    """)

    # Read csv file and insert data
    df = pd.read_csv(csv_file)
    df.to_sql("movies", conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()
    print("Database has been created")

# 运行数据加载
load_movies_into_db()