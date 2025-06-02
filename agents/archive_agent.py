import os
import shutil
import json
import sqlite3
import re
from datetime import datetime
from config import ARCHIVE_DIR, ARCHIVE_DB_PATH

class ArchiveAgent:
    def __init__(self, intermediate_path, original_pdf_path,
                 archive_dir=ARCHIVE_DIR, db_path=ARCHIVE_DB_PATH):
        # Übergabe der Pfade für die result.json und das Original-PDF
        self.intermediate_path = intermediate_path
        self.original_pdf_path = original_pdf_path
        self.archive_dir = archive_dir
        self.db_path = db_path

        # Stelle sicher, dass das Archiv-Verzeichnis existiert
        os.makedirs(self.archive_dir, exist_ok=True)

        # Initialisiere die SQLite-Datenbank für Archivierungseinträge
        self._init_db()

    def goal(self):
        # Ziel des Agenten: revisionssichere Archivierung der finalen Ergebnisse
        return "Speichere das abgeschlossene Ergebnis dauerhaft ab, damit es revisionssicher archiviert ist."

    def think(self):
        # Lade result.json als Grundlage für die Archivierung
        print("ArchiveAgent Think(): Lade Daten und bereite Archivierung vor.")
        with open(self.intermediate_path, "r", encoding="utf-8") as f:
            self.results = json.load(f)
        return self.results

    def action(self):
        # Hauptlogik der Archivierung
        data = self.think()

        # Rechnungsnummer aus der Validierungs-Tabelle extrahieren
        validation_table = data.get("validation", "")
        rechnungsnummer = self._extract_field(validation_table, "6. Fortlaufende Rechnungsnummer") or "unknown"

        # Bereinige Rechnungsnummer von Sonderzeichen (Doppelpunkt, Slash etc.)
        rechnungsnummer = re.sub(r"(Rechnungsnummer\s*[:\-]?\s*)", "", rechnungsnummer, flags=re.IGNORECASE)
        rechnungsnummer = rechnungsnummer.replace(":", "").replace("/", "").replace("\\", "").strip()

        # Verhindere doppelte Archivierung
        if self.is_already_archived(rechnungsnummer):
            return f"Archivierung abgebrochen - Rechnung {rechnungsnummer} wurde bereits archiviert."

        # Erstelle eindeutigen Ordnernamen mit Zeitstempel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{rechnungsnummer}_{timestamp}"
        folder_path = os.path.join(self.archive_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Kopiere result.json und PDF in das Archivverzeichnis
        shutil.copy(self.intermediate_path, os.path.join(folder_path, "results.json"))
        shutil.copy(self.original_pdf_path, os.path.join(folder_path, "invoice.pdf"))

        # Trage Archivpfad und Rechnungsnummer in die SQLite-Datenbank ein
        self._save_to_db(rechnungsnummer, folder_path)

        return f"Archiviert unter: {folder_path}"

    def _extract_field(self, markdown_table, label):
        # Extrahiere ein bestimmtes Feld aus der Markdown-Tabelle
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, markdown_table.replace("\n", " "))
        return match.group(2).strip() if match else None

    def _init_db(self):
        # Initialisiere Tabelle 'archive' in der SQLite-Datenbank, falls nicht vorhanden
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
        # Prüfe, ob eine Rechnung mit derselben Rechnungsnummer schon archiviert wurde
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM archive WHERE rechnungsnummer = ?", (rechnungsnummer,))
        count = c.fetchone()[0]
        conn.close()
        return count > 0

    def _save_to_db(self, rechnungsnummer, pfad):
        # Speichere Archivinformation (Rechnungsnummer, Zeit, Pfad) in die Datenbank
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO archive (rechnungsnummer, archiviert_am, pfad) VALUES (?, ?, ?)",
            (rechnungsnummer, datetime.now().isoformat(), pfad)
        )
        conn.commit()
        conn.close()
