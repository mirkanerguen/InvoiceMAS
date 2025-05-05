import os
import sqlite3

# Stelle sicher, dass der Ordner existiert
os.makedirs("data", exist_ok=True)

# Erstelle/verknüpfe Datenbank
conn = sqlite3.connect("data/archive.db")
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS archive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rechnungsnummer TEXT,
        archiviert_am TEXT,
        pfad TEXT
    )
""")

conn.commit()
conn.close()

print("Tabelle 'archive' wurde erfolgreich erstellt.")
