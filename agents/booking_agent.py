from langchain_community.llms import Ollama
import json
import re

class BookingAgent:
    def __init__(self, intermediate_path="data/intermediate_results.json"):
        self.llm = Ollama(model="mistral")
        self.path = intermediate_path
        with open(intermediate_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
    
    def goal(self):
        return "Führe die Buchung der freigegebenen Rechnung durch und kennzeichne sie als gebucht."

    def think(self):
        if self.data.get("status") == "gebucht":
            return "Diese Rechnung wurde bereits gebucht. Keine Aktion notwendig."
        return "Die Rechnung ist freigegeben und kann jetzt auf die zugewiesene Kostenstelle gebucht werden."

    def action(self):
        gedanke = self.think()
        if "bereits gebucht" in gedanke:
            return "⚠️ Rechnung bereits gebucht – keine doppelte Buchung."

        # Extrahiere Buchungsdaten
        kostenstelle = self.data.get("accounting", "Unbekannt")
        validation = self.data.get("validation", "")
        match = re.search(r"Netto[: ]*([\d\.,]+)", validation.replace("\n", " "))
        betrag = match.group(1).replace(".", "").replace(",", ".") if match else "0.00"

        # Erstelle Buchungsprompt
        buchung_prompt = f"""
Du bist ein Buchhaltungs-Agent. Dein Ziel: Simuliere die Buchung der Rechnung.

Rechnungsdaten:
- Kostenstelle: {kostenstelle}
- Betrag netto: {betrag} EUR

Generiere einen Buchungseintrag im folgenden Format:

📘 Buchung erfolgt: [Betrag] EUR auf [Kostenstelle] – Status: gebucht
"""
        buchung_text = self.llm.invoke(buchung_prompt).strip()

        # Speichere Status
        self.data["booking"] = buchung_text
        self.data["status"] = "gebucht"
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        return buchung_text
