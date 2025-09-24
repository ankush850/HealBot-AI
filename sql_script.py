# run_sql_script.py
import sqlite3

# Define the name for your SQLite database file
DB_FILE = "diseases.db"
# Define the path to your SQL script
SQL_FILE = "create_diseases_db.sql"

# Connect to the SQLite database (this will create the file if it doesn't exist)
con = sqlite3.connect(DB_FILE)
cur = con.cursor()

# Read the SQL script
with open(SQL_FILE, 'r') as f:
    sql_script = f.read()

# Execute the entire script
cur.executescript(sql_script)

print(f"✅ Database '{DB_FILE}' created successfully.")

# Commit the changes and close the connection
con.commit()
con.close()