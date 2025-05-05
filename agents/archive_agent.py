import os
import shutil
import json
import sqlite3
from datetime import datetime

class ArchiveAgent:
    def __init__(self, intermediate_path, original_pdf_path, archive_dir="archive", db_path="data/archive.db"):
        self.intermediate_path = intermediate_path
        self.original_pdf_path = original_pdf_path
        self.archive_dir = archive_dir
        self.db_path = db_path

        os.makedirs(archive_dir, exist_ok=True)
        self._init_db()

    def goal(self):
        return "Speichere das abgeschlossene Ergebnis dauerhaft ab, damit es revisionssicher archiviert ist."

    def think(self):
        print("ArchiveAgent Think(): Lade Daten und bereite Archivierung vor.")
        with open(self.intermediate_path, "r", encoding="utf-8") as f:
            self.results = json.load(f)
        return self.results

    def action(self):
        data = self.think()

        # Rechnungsnummer extrahieren (muss vor der Prüfung passieren!)
        validation_table = data.get("validation", "")
        rechnungsnummer = self._extract_field(validation_table, "6. Fortlaufende Rechnungsnummer") or "unknown"
        rechnungsnummer = rechnungsnummer.replace(":", "").replace("/", "").replace("\\", "").strip()

        # Prüfe, ob diese Rechnung schon archiviert wurde
        if self.is_already_archived(rechnungsnummer):
            return f"Archivierung abgebrochen – Rechnung {rechnungsnummer} wurde bereits archiviert."


        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        folder_name = f"{rechnungsnummer}_{timestamp}"
        folder_path = os.path.join(self.archive_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Speichere JSON
        shutil.copy(self.intermediate_path, os.path.join(folder_path, "results.json"))
        # Speichere PDF
        shutil.copy(self.original_pdf_path, os.path.join(folder_path, "invoice.pdf"))

        # Eintrag in DB
        self._save_to_db(rechnungsnummer, folder_path)

        return f"Archiviert unter: {folder_path}"

    def _extract_field(self, markdown_table, label):
        import re
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, markdown_table.replace("\n", " "))
        return match.group(2).strip() if match else None

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
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

    def is_already_archived(self, rechnungsnummer):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM archive WHERE rechnungsnummer = ?", (rechnungsnummer,))
        count = c.fetchone()[0]
        conn.close()
        return count > 0


    def _save_to_db(self, rechnungsnummer, pfad):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO archive (rechnungsnummer, archiviert_am, pfad) VALUES (?, ?, ?)",
                  (rechnungsnummer, datetime.now().isoformat(), pfad))
        conn.commit()
        conn.close()
