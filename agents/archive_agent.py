import json
import os
import shutil
import re
from datetime import datetime
from config import RESULTS_PATH, ARCHIVE_DIR
from langchain_community.llms import Ollama

class ArchiveAgent:
    def __init__(self, result_path=RESULTS_PATH):
        self.result_path = result_path
        self.llm = Ollama(model="mistral")

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        os.makedirs(ARCHIVE_DIR, exist_ok=True)

    def goal(self):
        return "Archivierung einer erfolgreich gebuchten Rechnung mit nachvollziehbarem Dateinamen."

    def prompt(self):
        invoice_number = self.extract_invoice_number()
        booking_status = self.data.get("booking_status", "unbekannt")
        return f"""
Du bist ein Archivierungs-Agent.

Rechnungsnummer: {invoice_number}
Status der Buchung: {booking_status}

Frage: Soll die Rechnung archiviert werden?
Antwort: Gib nur "ja" oder "nein" zurück.
"""

    def think(self):
        return "Ich prüfe den Buchungsstatus und entscheide anhand des LLM-Prompts, ob archiviert werden darf."

    def extract_invoice_number(self):
        match = re.search(r"\|\s*6\. Fortlaufende Rechnungsnummer\s*\|\s*Ja\s*\|\s*(.*?)\s*\|", self.data.get("validation", ""))
        return match.group(1).strip() if match else "UNBEKANNT"

    def action(self):
        print("ArchiveAgent Think():", self.think())

        invoice_number = self.extract_invoice_number()
        booking_status = self.data.get("booking_status", "").lower()

        # Genehmigung durch LLM
        decision = self.llm.invoke(self.prompt()).strip().lower()
        if decision != "ja":
            self.data["archive"] = "Archivierung abgelehnt durch KI."
            self.data["archived"] = False
            self._save()
            return self.data["archive"]

        # Pfad zur Originalrechnung aus results.json
        pdf_path = self.data.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            self.data["archive"] = "Fehler: PDF-Datei nicht vorhanden oder Pfad ungültig."
            self.data["archived"] = False
            self._save()
            return self.data["archive"]

        # Zielpfad erzeugen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = f"{invoice_number}_{timestamp}.pdf"
        target_path = os.path.join(ARCHIVE_DIR, target_name)

        shutil.copy2(pdf_path, target_path)
        self.data["archive"] = f"Archiviert unter: {target_path}"
        self.data["archived"] = True
        self._save()

        print("ArchiveAgent Action():", self.data["archive"])
        return self.data["archive"]

    def _save(self):
        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
