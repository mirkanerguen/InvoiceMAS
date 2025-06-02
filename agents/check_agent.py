# check_agent.py
import json
import re
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from config import RESULTS_PATH, REFERENCE_DATA_PATH, OLLAMA_MODEL

class CheckAgent:
    def __init__(self, validation_result_path=RESULTS_PATH, reference_path=REFERENCE_DATA_PATH):
        # LLM initialisieren
        self.llm = Ollama(model=OLLAMA_MODEL)

        # Validierungsdaten aus results.json laden
        with open(validation_result_path, "r", encoding="utf-8") as f:
            self.raw_data = json.load(f).get("validation", "")

        # Referenztransaktionen (bekannte Rechnungen) laden
        with open(reference_path, "r", encoding="utf-8") as f:
            self.known = json.load(f).get("invoices", [])

        # Text normalisieren, um Verarbeitung zu erleichtern
        self.data = self._normalize_text(self.raw_data)

    def goal(self):
        # Zieldefinition für die LLM-Prompt
        return "Prüfe die sachliche Richtigkeit einer Rechnung mit Fokus auf Rechnungsnummer, plausiblen Lieferanten, Leistung und Bruttobetrag."

    def think(self):
        # Extrahiere die 4 wichtigsten Vergleichswerte für die sachliche Prüfung
        return {
            "rechnungsnummer": self._extract("6. Fortlaufende Rechnungsnummer"),
            "lieferant": self._extract("1. Name & Anschrift des leistenden Unternehmers"),
            "leistung": self._extract("7. Menge und Art der gelieferten Leistung"),
            "betrag": self._extract("9. Entgelt nach Steuersätzen aufgeschlüsselt")
        }

    def action(self):
        # Extrahierte Werte sammeln
        extracted = self.think()
        brutto = self._extract_bruttobetrag(extracted["betrag"])

        # Referenzdaten zur passenden Rechnungsnummer suchen
        referenz = next(
            (r for r in self.known if r["rechnungsnummer"].strip() == extracted["rechnungsnummer"].strip()),
            None
        )

        # Wenn keine passende Referenz gefunden wird → negativ abschließen
        if not referenz:
            self._save_result("nicht_nachvollziehbar")
            return "nicht_nachvollziehbar"

        # Rechnung und Referenz schön formatiert als Text darstellen
        referenz_text = (
            f"Rechnungsnummer: {referenz['rechnungsnummer']}\n"
            f"Lieferant: {referenz['lieferant']}\n"
            f"Leistung: {referenz['leistung']}\n"
            f"Brutto: {referenz['betrag_brutto']:.2f} EUR"
        )
        rechnung_text = (
            f"Rechnungsnummer: {extracted['rechnungsnummer']}\n"
            f"Lieferant: {extracted['lieferant']}\n"
            f"Leistung: {extracted['leistung']}\n"
            f"Brutto: {brutto} EUR"
        )

        # Prompt-Vorlage für die LLM-Prüfung definieren
        prompt_template = PromptTemplate(
            input_variables=["ziel", "rechnung", "referenz"],
            template="""
Du bist ein KI-Agent für Rechnungsprüfung.

Aufgabe: {ziel}

Prüfe, ob folgende Inhalte sachlich plausibel übereinstimmen:

Rechnung:
{rechnung}

Referenzdaten:
{referenz}

Kriterien:
- Lieferant darf sprachlich leicht abweichen, aber inhaltlich gleich sein.
- Leistung kann in anderer Reihenfolge oder Formulierung vorliegen.
- Bruttobetrag darf max. um 0.01 € abweichen.
- Wenn alles inhaltlich passt → "sachlich_korrekt", sonst "nicht_nachvollziehbar".
"""
        )

        # Prompt ausfüllen und LLM aufrufen
        prompt = prompt_template.format(
            ziel=self.goal(),
            rechnung=rechnung_text,
            referenz=referenz_text
        )
        result = self.llm.invoke(prompt).strip().lower()

        # Ergebnis prüfen und speichern
        if "sachlich_korrekt" in result:
            self._save_result("sachlich_korrekt")
            return "sachlich_korrekt"
        elif "nicht_nachvollziehbar" in result:
            self._save_result("nicht_nachvollziehbar")
            return "nicht_nachvollziehbar"

        # Falls etwas unklar bleibt (z. B. schlechte LLM-Antwort), "unklar" setzen
        self._save_result("unklar")
        return "unklar"

    def _save_result(self, result_value):
        # Ergebnis in results.json speichern
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        data["check"] = result_value
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _extract(self, label):
        # Extrahiere einzelne Zellen aus der Markdown-Tabelle (Pflichtangaben)
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, self.data.replace("\n", " "))
        return match.group(2).strip() if match else "unbekannt"

    def _extract_bruttobetrag(self, betrag_text):
        # Versuche, den Bruttobetrag aus dem extrahierten Text direkt zu parsen
        match = re.search(r"gesamt[:\s]*([\d\.,]+)", betrag_text.lower())
        return match.group(1).replace(",", ".") if match else "0.00"

    def _normalize_text(self, text):
        # HTML-Zeilenumbrüche ersetzen, Sonderzeichen säubern
        text = text.replace("<br>", ", ")
        text = text.replace("€", "EUR")
        text = text.replace("\u00a0", " ")
        return text
