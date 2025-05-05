import os

db_path = "invoice_archive.db"

if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✅ Datenbank '{db_path}' wurde erfolgreich gelöscht.")
else:
    print(f"❌ Datenbank '{db_path}' existiert nicht.")
