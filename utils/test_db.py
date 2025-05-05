import sqlite3
import pandas as pd

conn = sqlite3.connect("invoice_archive.db")

# Prüfe, ob die Tabelle existiert
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archive'")
if cursor.fetchone():
    df = pd.read_sql_query("SELECT * FROM archive", conn)
    print("✅ Tabelle gefunden:\n", df)
else:
    print("❌ Tabelle 'archive' existiert nicht.")

conn.close()
