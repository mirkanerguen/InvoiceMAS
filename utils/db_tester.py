import sqlite3

conn = sqlite3.connect("data/archive.db")
cursor = conn.cursor()
for row in cursor.execute("SELECT * FROM archive"):
    print(row)
conn.close()
