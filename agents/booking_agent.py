from langchain_community.llms import Ollama
import json
import re
import sqlite3

class BookingAgent:
    def __init__(self, intermediate_path="data/results.json"):
        self.llm = Ollama(model="mistral")
        self.path = intermediate_path
        with open(intermediate_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def goal(self):
        return "Führe die Buchung der freigegebenen Rechnung durch und kennzeichne sie als gebucht."

    def think(self):
        if self.data.get("booking_status") == "gebucht":
            return "Diese Rechnung wurde bereits gebucht. Keine Aktion notwendig."
        return "Die Rechnung ist freigegeben und kann jetzt gebucht werden."

    def is_invoice_already_booked(self, rechnungsnummer: str) -> bool:
        conn = sqlite3.connect("data/archive.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE rechnungsnummer = ?", (rechnungsnummer,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def action(self):
        gedanke = self.think()
        validation = self.data.get("validation", "")

        match_nr = re.search(r"\|6\. Fortlaufende Rechnungsnummer\s*\|\s*Ja\s*\|\s*(.*?)\s*\|", validation)
        rechnungsnummer = match_nr.group(1).strip() if match_nr else "UNBEKANNT"

        if self.is_invoice_already_booked(rechnungsnummer):
            result = f"Buchung abgebrochen – Rechnung {rechnungsnummer} wurde bereits gebucht."
            self.data["booking"] = result
            self.data["booking_status"] = "abgebrochen"
            self._save()
            return result

        kostenstelle = self.data.get("accounting", "Unbekannt")
        match_betrag = re.search(r"Brutto[: ]*([\d\.,]+)", validation.replace("\n", " "))
        betrag = match_betrag.group(1).replace(".", "").replace(",", ".") if match_betrag else "0.00"

        buchung_prompt = f"""
Du bist ein Buchhaltungs-Agent. Dein Ziel: Simuliere die Buchung der Rechnung.

Rechnungsdaten:
- Kostenstelle: {kostenstelle}
- Betrag brutto: {betrag} EUR

Gib folgenden Satz aus:

Buchung erfolgt: [Betrag] EUR auf [Kostenstelle] – Status: gebucht
"""
        buchung_text = self.llm.invoke(buchung_prompt).strip()

        self.data["booking"] = buchung_text
        self.data["booking_status"] = "gebucht"
        self._save()

        return buchung_text

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
