import sqlite3
import os

# Basisverzeichnis ermitteln (z. B. .../InvoiceMAS/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(BASE_DIR, "data")
db_path = os.path.join(data_dir, "archive.db")

# Sicherstellen, dass der Datenordner existiert
os.makedirs(data_dir, exist_ok=True)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rechnungsnummer TEXT,
            archiviert_am TEXT,
            pfad TEXT
        )
    """)
    conn.commit()
    print("Tabelle 'archive' wurde erfolgreich erstellt unter:", db_path)
except Exception as e:
    print(f"Fehler beim Erstellen der Tabelle: {e}")
finally:
    conn.close()
