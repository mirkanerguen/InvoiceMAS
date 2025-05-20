import json
import re
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from config import RESULTS_PATH, REFERENCE_DATA_PATH, OLLAMA_MODEL

class CheckAgent:
    def __init__(self, validation_result_path=RESULTS_PATH, reference_path=REFERENCE_DATA_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)
        with open(validation_result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f).get("validation", "")
        with open(reference_path, "r", encoding="utf-8") as f:
            self.known = json.load(f).get("invoices", [])

    def goal(self):
        return "Prüfe die sachliche Richtigkeit einer Rechnung mit Fokus auf exakte Rechnungsnummer und semantisch plausible Übereinstimmung weiterer Felder."

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
        brutto = self._extract_bruttobetrag(extracted["betrag"])
        referenz = next(
            (r for r in self.known if r["rechnungsnummer"].strip() == extracted["rechnungsnummer"].strip()),
            None
        )

        if not referenz:
            print("CheckAgent Action(): Rechnungsnummer nicht bekannt → nicht nachvollziehbar.")
            return "nicht_nachvollziehbar"

        referenzliste = (
            f"- Rechnungsnr: {referenz['rechnungsnummer']}, Lieferant: {referenz['lieferant']}, "
            f"Leistung: {referenz['leistung']}, Brutto: {referenz['betrag_brutto']} €"
        )
        rechnung_text = (
            f"Rechnungsnummer: {extracted['rechnungsnummer']}\n"
            f"Lieferant: {extracted['lieferant']}\n"
            f"Leistung: {extracted['leistung']}\n"
            f"Brutto-Betrag: {brutto} EUR"
        )

        prompt_template = PromptTemplate(
            input_variables=["ziel", "rechnung", "referenz"],
            template="""Du bist ein KI-Agent zur sachlichen Prüfung einer Rechnung.

Dein Ziel lautet: {ziel}

Hier ist die zu prüfende Rechnung:
{rechnung}

Hier ist die bekannte Referenzrechnung:
{referenz}

Vergleiche die Inhalte. Achte auf sinngemäße Übereinstimmung bei Lieferant, Leistung und Bruttobetrag.
Wenn alles plausibel übereinstimmt, antworte mit "sachlich_korrekt", sonst mit "nicht_nachvollziehbar".
"""
        )

        prompt = prompt_template.format(
            ziel=self.goal(),
            rechnung=rechnung_text,
            referenz=referenzliste
        )

        result = self.llm.invoke(prompt).strip().lower()

        if result == "sachlich_korrekt":
            print("CheckAgent Action(): sachlich korrekt (LLM-Einschätzung)")
            return "sachlich_korrekt"
        elif result == "nicht_nachvollziehbar":
            print("CheckAgent Action(): nicht nachvollziehbar (LLM-Einschätzung)")
            return "nicht_nachvollziehbar"
        else:
            print("CheckAgent Action(): unklar - LLM-Antwort nicht eindeutig.")
            return "unklar"

    def _extract(self, label):
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, self.data.replace("\n", " "))
        return match.group(2).strip() if match else "unbekannt"

    def _extract_bruttobetrag(self, betrag_text):
        match = re.search(r"Brutto[: ]*([\d\.,]+)", betrag_text)
        return match.group(1).replace(",", ".") if match else "0.00"
