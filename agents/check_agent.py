import json
import re
from config import RESULTS_PATH, REFERENCE_DATA_PATH
from langchain_community.llms import Ollama

class CheckAgent:
    def __init__(self, result_path=RESULTS_PATH, known_path=REFERENCE_DATA_PATH):
        self.result_path = result_path
        self.known_path = known_path
        self.llm = Ollama(model="mistral")

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        try:
            with open(self.known_path, "r", encoding="utf-8") as f:
                self.known_data = json.load(f)
                self.known = self.known_data.get("invoices", [])
        except FileNotFoundError:
            self.known = []

    def goal(self):
        return "Prüfe die sachliche Korrektheit der Rechnung durch Vergleich mit bekannten Transaktionen."

    def prompt(self, extracted, known_matches):
        return f"""
Du bist ein sachlicher Prüfagent. Ziel: Vergleiche die folgende Eingangsrechnung mit bekannten Transaktionen und bewerte die sachliche Plausibilität.

Rechnungsdaten:
- Rechnungsnummer: {extracted.get("rechnungsnummer")}
- Lieferant: {extracted.get("lieferant")}
- Leistung: {extracted.get("leistung")}
- Betrag: {extracted.get("betrag")} EUR

Bekannte Vergleichseinträge:
{known_matches}

Antwortmöglichkeiten:
- sachlich_korrekt
- nicht_nachvollziehbar
- unklar

Gib **nur eine dieser Antworten** zurück.
"""

    def think(self):
        return "Ich vergleiche extrahierte Rechnungsangaben mit der Referenzdatenbank für sachliche Prüfung."

    def extract_fields(self):
        validation = self.data.get("validation", "")
        fields = {}

        patterns = {
            "rechnungsnummer": r"\| 6\. Fortlaufende Rechnungsnummer \|\s*Ja\s*\|\s*(.*?)\s*\|",
            "lieferant": r"\| 1\. Name & Anschrift des leistenden Unternehmers \|\s*Ja\s*\|\s*(.*?)\s*\|",
            "leistung": r"\| 7\. Menge und Art der gelieferten Leistung \|\s*Ja\s*\|\s*(.*?)\s*\|",
            "betrag": r"Brutto.*?([\d.,]+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, validation.replace("\n", " "))
            if match:
                value = match.group(1).strip().replace(",", ".")
                fields[key] = value
            else:
                fields[key] = "unbekannt"

        print("[DEBUG] Extrahierte Felder:", fields)
        return fields

    def find_similar(self, extracted):
        matches = []
        try:
            betrag_ext = float(extracted.get("betrag", 0))
        except ValueError:
            print("[WARNUNG] Betrag nicht interpretierbar:", extracted.get("betrag"))
            return matches

        for entry in self.known:
            try:
                betrag_known = float(entry.get("betrag_brutto", 0))
                if entry.get("rechnungsnummer") == extracted.get("rechnungsnummer"):
                    matches.append(entry)
                elif abs(betrag_known - betrag_ext) < 10:
                    matches.append(entry)
            except (ValueError, TypeError):
                continue

        return matches

    def action(self):
        print("CheckAgent Think():", self.think())
        extracted = self.extract_fields()
        similar = self.find_similar(extracted)

        if not similar:
            print("Keine vergleichbaren Transaktionen gefunden.")
            result = "nicht_nachvollziehbar"
        else:
            known_text = json.dumps(similar, indent=2, ensure_ascii=False)
            decision = self.llm.invoke(self.prompt(extracted, known_text)).strip().lower()
            result = decision if decision in ["sachlich_korrekt", "nicht_nachvollziehbar", "unklar"] else "unklar"

        self.data["check"] = result
        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        print(f"CheckAgent Action(): {result}")
        return result
