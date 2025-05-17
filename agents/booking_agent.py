import json
import re
import sqlite3
from langchain_community.llms import Ollama
from config import RESULTS_PATH, ARCHIVE_DB_PATH, OLLAMA_MODEL

class BookingAgent:
    def __init__(self, intermediate_path=RESULTS_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.path = intermediate_path

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def goal(self):
        return "Führe die Buchung der freigegebenen Rechnung durch und kennzeichne sie als gebucht."

    def think(self):
        if self.data.get("booking_status") == "gebucht":
            return "Diese Rechnung wurde bereits gebucht. Keine Aktion notwendig."
        return "Die Rechnung ist freigegeben und kann jetzt gebucht werden."

    def is_invoice_already_booked(self, rechnungsnummer: str) -> bool:
        conn = sqlite3.connect(ARCHIVE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE rechnungsnummer = ?", (rechnungsnummer,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def extract_amount_with_llm(self, validation_text: str) -> str:
        prompt = f"""
    Du bist ein Buchhaltungsassistent. Extrahiere aus dem folgenden Text den **Bruttobetrag der Rechnung** in Euro.
    Text:
    {validation_text}

    Gib nur den Betrag in dieser Form zurück, z. B.: 1200.00
    """
        response = self.llm.invoke(prompt).strip()

        match = re.search(r"([\d]+[\.,]?[\d]*)", response)
        if match:
            betrag = match.group(1).replace(",", ".")
            try:
                float(betrag)
                return betrag
            except ValueError:
                pass
        return "0.00"

    def action(self):
        gedanke = self.think()
        validation = self.data.get("validation", "")

        # Rechnungsnummer extrahieren
        match_nr = re.search(r"\|6\. Fortlaufende Rechnungsnummer\s*\|\s*Ja\s*\|\s*(.*?)\s*\|", validation)
        rechnungsnummer = match_nr.group(1).strip() if match_nr else "UNBEKANNT"

        # Prüfen, ob bereits gebucht
        if self.is_invoice_already_booked(rechnungsnummer):
            result = f"Buchung abgebrochen - Rechnung {rechnungsnummer} wurde bereits gebucht."
            self.data["booking"] = result
            self.data["booking_status"] = "abgebrochen"
            self._save()
            return result

        # Kostenstelle und Bruttobetrag extrahieren
        kostenstelle = self.data.get("accounting", "Unbekannt")
        betrag = self.extract_amount_with_llm(validation)

        # Prompt zur simulierten Buchung
        buchung_prompt = f"""
Du bist ein Buchhaltungs-Agent. Dein Ziel: Simuliere die Buchung der Rechnung.

Rechnungsdaten:
- Kostenstelle: {kostenstelle}
- Betrag brutto: {betrag} EUR

Gib folgenden Satz exakt aus:
Buchung erfolgt: [Betrag] EUR auf [Kostenstelle] - Status: gebucht
"""
        buchung_text = self.llm.invoke(buchung_prompt).strip()

        # Ergebnisse speichern
        self.data["booking"] = buchung_text
        self.data["booking_status"] = "gebucht"
        self._save()

        return buchung_text

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
