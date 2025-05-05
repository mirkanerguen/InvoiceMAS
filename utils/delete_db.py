import os
import shutil

DB_PATH = "data/archive.db"
ARCHIVE_DIR = "archive"

def delete_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Datenbankdatei '{DB_PATH}' wurde erfolgreich gelöscht.")
    else:
        print(f"Keine Datenbankdatei unter '{DB_PATH}' gefunden.")

def delete_archive_folder():
    if os.path.exists(ARCHIVE_DIR):
        shutil.rmtree(ARCHIVE_DIR)
        print(f"Archivordner '{ARCHIVE_DIR}' wurde erfolgreich gelöscht.")
    else:
        print(f"Kein Archivordner unter '{ARCHIVE_DIR}' gefunden.")

if __name__ == "__main__":
    confirm = input("Möchtest du die Datenbank und alle archivierten Rechnungen löschen? (ja/nein): ").lower()
    if confirm == "ja":
        delete_database()
        delete_archive_folder()
    else:
        print("Vorgang abgebrochen.")
