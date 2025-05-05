import sqlite3

conn = sqlite3.connect("data/archive.db")  # Achte auf den korrekten Pfad zur DB
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
