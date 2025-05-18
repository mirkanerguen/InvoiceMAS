import json
import re
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from config import RESULTS_PATH, REFERENCE_DATA_PATH, OLLAMA_MODEL
from utils.invoice_comparator import compare_invoice_with_reference


class CheckAgent:
    def __init__(self, validation_result_path=RESULTS_PATH, reference_path=REFERENCE_DATA_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)

        with open(validation_result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f).get("validation", "")

        with open(reference_path, "r", encoding="utf-8") as f:
            self.known = json.load(f).get("invoices", [])

    def goal(self):
        return "Prüfe die sachliche Richtigkeit einer Rechnung auf Basis interner Referenzdaten."

    def think(self):
        print("CheckAgent Think(): Extrahiere relevante Felder.")
        return {
            "rechnungsnummer": self._extract("6. Fortlaufende Rechnungsnummer"),
            "lieferant": self._extract("1. Name & Anschrift des leistenden Unternehmers"),
            "leistung": self._extract("7. Menge und Art der gelieferten Leistung"),
            "betrag": self._extract("9. Entgelt nach Steuersätzen aufgeschlüsselt")
        }

    def action(self):
        extracted = self.think()

        # Bruttobetrag aus extrahierten Werten ziehen
        brutto_match = re.search(r"Brutto[: ]*([\d\.,]+)", extracted["betrag"])
        brutto_betrag = brutto_match.group(1).replace(",", ".") if brutto_match else "0.00"

        match_found = compare_invoice_with_reference(
            rechnungsnummer=extracted["rechnungsnummer"],
            lieferant=extracted["lieferant"],
            leistung=extracted["leistung"],
            betrag=brutto_betrag,
            reference_data=self.known
        )


        if match_found:
            print("CheckAgent Action(): sachlich korrekt (regelbasiert bestätigt)")
            return "sachlich_korrekt"

        # Wenn kein exakter Match: LLM zur finalen Bewertung
        referenzliste = "\n".join([
            f"- Rechnungsnr: {ref['rechnungsnummer']}, Lieferant: {ref['lieferant']}, "
            f"Leistung: {ref['leistung']}, Brutto: {ref['betrag_brutto']} €"
            for ref in self.known
        ])

        rechnung_text = (
            f"Rechnungsnummer: {extracted['rechnungsnummer']}\n"
            f"Lieferant: {extracted['lieferant']}\n"
            f"Leistung: {extracted['leistung']}\n"
            f"Brutto-Betrag: {brutto_betrag} EUR"
        )

        prompt_template = PromptTemplate(
            input_variables=["ziel", "rechnung", "referenzen"],
            template="""Du bist ein KI-Agent zur sachlichen Prüfung von Rechnungen.

Dein Ziel lautet: {ziel}

### Extrahierte Rechnung:
{rechnung}

### Interne Referenzrechnungen:
{referenzen}

Vergleiche Rechnung und Referenzen (semantisch und sachlich). 
Wenn keine ausreichende Übereinstimmung vorhanden ist, gilt die Rechnung als nicht nachvollziehbar.

Antwort nur mit einem Wort:
- sachlich_korrekt
- nicht_nachvollziehbar
"""
        )

        prompt = prompt_template.format(
            ziel=self.goal(),
            rechnung=rechnung_text,
            referenzen=referenzliste
        )

        result = self.llm.invoke(prompt).strip().lower()

        if result == "sachlich_korrekt":
            print("CheckAgent Action(): sachlich korrekt (LLM-Einschätzung)")
            return "sachlich_korrekt"
        elif result == "nicht_nachvollziehbar":
            print("CheckAgent Action(): nicht nachvollziehbar (LLM-Einschätzung)")
            return "nicht_nachvollziehbar"
        else:
            print("CheckAgent Action(): unklar – LLM-Antwort nicht eindeutig.")
            return "unklar"

    def _extract(self, label):
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, self.data.replace("\n", " "))
        return match.group(2).strip() if match else "unbekannt"
