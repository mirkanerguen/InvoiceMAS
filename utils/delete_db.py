import sqlite3
import os

# Basisverzeichnis 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(BASE_DIR, "data")
db_path = os.path.join(data_dir, "archive.db")

if not os.path.exists(db_path):
    print(f"Keine Datenbankdatei unter '{db_path}' gefunden.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM archive")  # Alle Zeilen löschen
        conn.commit()

        print(f"Alle Einträge in der Tabelle 'archive' wurden gelöscht ({db_path}).")
    except Exception as e:
        print(f"Fehler beim Leeren der Datenbank: {e}")
    finally:
        conn.close()
