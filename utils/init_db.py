import sqlite3

# Verbindung zur SQLite-Datenbank (Datei wird erstellt, falls sie nicht existiert)
conn = sqlite3.connect("invoice_archive.db")
cursor = conn.cursor()

# Tabelle 'archive' erstellen, falls nicht vorhanden
cursor.execute("""
    CREATE TABLE IF NOT EXISTS archive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rechnungsnummer TEXT,
        kostenstelle TEXT,
        betrag REAL,
        pfad TEXT,
        timestamp TEXT
    )
""")

conn.commit()
conn.close()

print("✅ Tabelle 'archive' wurde erfolgreich erstellt.")
