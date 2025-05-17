import json
from langchain_community.llms import Ollama
from utils.pdf_parser import extract_text_from_pdf
from config import RESULTS_PATH, OLLAMA_MODEL

class ValidationAgent:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.text = extract_text_from_pdf(pdf_path)

        # Lade bestehende Ergebnisse
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                self.results = json.load(f)
        except FileNotFoundError:
            self.results = {}

    def goal(self):
        return "Extrahiere und überprüfe die 12 Pflichtangaben gemäß §14 Abs. 4 UStG aus einer Rechnung."

    def prompt(self):
        return f"""
Du bist ein Validation-Agent. Deine Aufgabe ist es, aus folgendem Rechnungstext die 12 Pflichtangaben gemäß §14 Abs. 4 UStG zu prüfen und zu extrahieren.
Bitte achte genau auf die Position im Dokument: 
- Der **Leistungserbringer** steht üblicherweise **oben auf der Rechnung**.
- Der **Leistungsempfänger (Kunde)** steht meist weiter unten oder ist mit "Kunde", "Kundennummer" etc. markiert.

**Gib die Antwort ausschließlich in folgender Markdown-Tabelle zurück:**
| Pflichtangabe | Vorhanden | Extrahierter Wert |
|---------------|-----------|-------------------|
| 1. Name & Anschrift des leistenden Unternehmers | Ja/Nein | ... |
| 2. Name & Anschrift des Leistungsempfängers | Ja/Nein | ... |
| 3. Steuernummer des Unternehmers | Ja/Nein | ... |
| 4. Umsatzsteuer-ID des Unternehmers | Ja/Nein | ... |
| 5. Ausstellungsdatum | Ja/Nein | ... |
| 6. Fortlaufende Rechnungsnummer | Ja/Nein | ... |
| 7. Menge und Art der gelieferten Leistung | Ja/Nein | ... |
| 8. Zeitpunkt der Leistung oder Leistungszeitraum | Ja/Nein | ... |
| 9. Entgelt nach Steuersätzen aufgeschlüsselt | Ja/Nein | ... |
| 10. Steuersatz oder Hinweis auf Steuerbefreiung | Ja/Nein | ... |
| 11. Hinweis auf Aufbewahrungspflicht (§14b UStG) | Ja/Nein | ... |
| 12. Angabe „Gutschrift“ (falls zutreffend) | Ja/Nein | ... |

Rechnungstext:
{self.text}
"""

    def think(self):
        print("ValidationAgent: LLM wird mit Prompt versorgt...")
        return self.llm.invoke(self.prompt()).strip()

    def action(self):
        result_table = self.think()
        self.results["validation"] = result_table

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)

        print("ValidationAgent: Ergebnis in results.json gespeichert.")
        return result_table
