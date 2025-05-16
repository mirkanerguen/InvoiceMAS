import json
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from utils.check_utils import hard_match_check
from config import RESULTS_PATH, REFERENCE_DATA_PATH, OLLAMA_MODEL


class CheckAgent:
    def __init__(self, validation_result_path=RESULTS_PATH, reference_path=REFERENCE_DATA_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)

        with open(validation_result_path, "r", encoding="utf-8") as f:
            self.validation_table = json.load(f).get("validation", "")

        with open(reference_path, "r", encoding="utf-8") as f:
            self.known = json.load(f).get("invoices", [])

    def goal(self):
        return "Vergleiche die Rechnung mit vorhandenen Referenzen, um die sachliche Richtigkeit mit KI zu bewerten."

    def think(self):
        print("CheckAgent Think(): Extrahiere relevante Felder.")
        extraction_prompt = f"""
Du bist ein Extraktions-Agent für Rechnungsdaten.

Hier ist eine Tabelle mit Pflichtangaben einer Rechnung (Format: Markdown):

{self.validation_table}

Extrahiere folgende Felder präzise in JSON:

{{
  "rechnungsnummer": "...",
  "lieferant": "...",
  "leistung": "...",
  "betrag": "..."  // Entnimm den Bruttobetrag
}}

Achte auf sauberes JSON, keine Erklärungen.
"""

        response = self.llm.invoke(extraction_prompt).strip()

        try:
            data = json.loads(response)
            print("CheckAgent Think(): Extraktion erfolgreich.")
            return data
        except Exception as e:
            print("Fehler: KI-Antwort konnte nicht als JSON interpretiert werden.")
            print("Antwort war:", response)
            return {}

    def action(self):
        extracted = self.think()

        if not extracted:
            return "nicht_nachvollziehbar"

        if hard_match_check(extracted, self.known):
            print("CheckAgent Action(): sachlich korrekt")
            return "sachlich_korrekt"
        else:
            print("CheckAgent Action(): nicht nachvollziehbar (Abweichung festgestellt)")
            return "nicht_nachvollziehbar"
