import json
import os
import shutil
from datetime import datetime
from config import RESULTS_PATH
from langchain_community.llms import Ollama

class ArchiveAgent:
    def __init__(self, result_path=RESULTS_PATH, pdf_path=None):
        self.result_path = result_path
        self.pdf_path = pdf_path
        self.llm = Ollama(model="mistral")

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def goal(self):
        return "Archivierung der gebuchten Rechnung mit nachvollziehbarem Dateinamen im Archivordner."

    def prompt(self, invoice_number, booking_status):
        return f"""
Du bist ein Archivierungs-Agent. Die Rechnung mit der Nummer {invoice_number} wurde {booking_status}.

Deine Aufgabe:
Bestimme, ob die Rechnung archiviert werden darf. Gib nur "ja" oder "nein" zurück.
"""

    def think(self):
        return "Wenn die Buchung erfolgreich war, darf archiviert werden."

    def extract_invoice_number(self):
        match = None
        if "validation" in self.data:
            import re
            match = re.search(r"\| 6\. Fortlaufende Rechnungsnummer \|\s*Ja\s*\|\s*(.*?)\s*\|", self.data["validation"])
        return match.group(1).strip() if match else "UNBEKANNT"

    def action(self):
        print("ArchiveAgent Think():", self.think())

        invoice_number = self.extract_invoice_number()
        booking_status = self.data.get("booking_status", "").lower()

        decision = self.llm.invoke(self.prompt(invoice_number, booking_status)).strip().lower()
        if decision != "ja":
            self.data["archive"] = "Archivierung übersprungen durch KI-Entscheidung."
            self.data["archived"] = False
            print("ArchiveAgent: Archivierung verweigert.")
            self._save()
            return self.data["archive"]

        # Archivordner vorbereiten
        archive_dir = "archive"
        os.makedirs(archive_dir, exist_ok=True)

        # Dateiname generieren
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{invoice_number}_{timestamp}.pdf"
        archive_path = os.path.join(archive_dir, filename)

        # PDF kopieren
        if self.pdf_path and os.path.exists(self.pdf_path):
            shutil.copy2(self.pdf_path, archive_path)
            self.data["archive"] = f"Archiviert unter: {archive_path}"
            self.data["archived"] = True
        else:
            self.data["archive"] = "PDF-Datei nicht gefunden – Archivierung fehlgeschlagen."
            self.data["archived"] = False

        print("ArchiveAgent Action():", self.data["archive"])
        self._save()
        return self.data["archive"]

    def _save(self):
        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
