import json
import re
import sqlite3
from config import RESULTS_PATH, ARCHIVE_DB_PATH, OLLAMA_MODEL
from langchain_community.llms import Ollama

class BookingAgent:
    def __init__(self, result_path=RESULTS_PATH):
        self.result_path = result_path
        self.llm = Ollama(model=OLLAMA_MODEL)

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.validation_text = self.data.get("validation", "")
        self.cost_center = self.data.get("accounting", "Unbekannt")

    def goal(self):
        return "Führe die Buchung der freigegebenen Rechnung durch und kennzeichne sie als gebucht."

    def prompt(self, amount):
        return f"""
Du bist ein Buchhaltungsagent. Simuliere eine Buchung auf Basis der folgenden Informationen:

- Betrag: {amount} EUR
- Kostenstelle: {self.cost_center}

Antworte mit genau folgendem Format:
Buchung erfolgt: [Betrag] EUR auf [Kostenstelle] - Status: gebucht
"""

    def think(self):
        if self.data.get("booking_status") == "gebucht":
            return "Rechnung wurde bereits gebucht. Keine Aktion notwendig."
        return "Rechnung wurde genehmigt und kann jetzt gebucht werden."

    def is_already_booked(self, invoice_number):
        conn = sqlite3.connect(ARCHIVE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE rechnungsnummer = ?", (invoice_number,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def extract_invoice_number(self):
        match = re.search(r"\| 6\. Fortlaufende Rechnungsnummer \|\s*Ja\s*\|\s*(.*?)\s*\|", self.validation_text)
        return match.group(1).strip() if match else "UNBEKANNT"

    def extract_amount(self):
        match = re.search(r"Brutto.*?([\d.,]+)", self.validation_text.replace("\n", " "))
        if match:
            try:
                return float(match.group(1).replace(".", "").replace(",", "."))
            except:
                pass
        return 0.0

    def action(self):
        print("BookingAgent Think():", self.think())
        invoice_number = self.extract_invoice_number()

        if self.is_already_booked(invoice_number):
            msg = f"Buchung abgebrochen - Rechnung {invoice_number} wurde bereits gebucht."
            self.data["booking"] = msg
            self.data["booking_status"] = "abgebrochen"
        else:
            amount = self.extract_amount()
            self.data["booking_amount"] = amount

            prompt = self.prompt(amount)
            booking_text = self.llm.invoke(prompt).strip()

            self.data["booking"] = booking_text
            self.data["booking_status"] = "gebucht"

        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        print("BookingAgent Action():", self.data["booking"])
        return self.data["booking"]
