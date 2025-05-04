import json
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
import re

class CheckAgent:
    def __init__(self, validation_result_path="data/intermediate_results.json", reference_path="data/known_transactions.json"):
        self.llm = Ollama(model="mistral")
        with open(validation_result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)["validation"]
        with open(reference_path, "r", encoding="utf-8") as f:
            self.known = json.load(f)["invoices"]

    def goal(self):
        return "Vergleiche die Rechnung mit vorhandenen Referenzen, um die sachliche Richtigkeit mit KI zu bewerten."

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

        # Bereite bekannte Daten als Liste auf
        referenzliste = ""
        for ref in self.known:
            referenzliste += f"- Rechnungsnr: {ref['rechnungsnummer']}, Lieferant: {ref['lieferant']}, Leistung: {ref['leistung']}, Netto: {ref['betrag_netto']} €\n"

        # Prompt definieren
        prompt_template = PromptTemplate(
            input_variables=["ziel", "rechnung", "referenzen"],
            template="""Du bist ein KI-Agent zur sachlichen Prüfung von Rechnungen.

Dein Ziel lautet: {ziel}

Gegeben ist die extrahierte Rechnung:
{rechnung}

Und hier sind bekannte interne Referenzrechnungen:
{referenzen}

Vergleiche die Inhalte intelligent (auch semantisch) und antworte nur mit:
- ✅ Sachlich korrekt (wenn plausible Übereinstimmung besteht)
- ❌ Sachlich nicht nachvollziehbar (wenn kein plausibler Bezug gefunden wird)
"""
        )

        # Betrag normalisieren
        netto_match = re.search(r"Netto[: ]*([\d\.,]+)", extracted["betrag"])
        netto = netto_match.group(1) if netto_match else "unbekannt"

        rechnung_text = (
            f"Rechnungsnummer: {extracted['rechnungsnummer']}\n"
            f"Lieferant: {extracted['lieferant']}\n"
            f"Leistung: {extracted['leistung']}\n"
            f"Netto-Betrag: {netto} €"
        )

        prompt = prompt_template.format(
            ziel=self.goal(),
            rechnung=rechnung_text,
            referenzen=referenzliste
        )

        result = self.llm.invoke(prompt).strip()
        print("CheckAgent Action():", result)
        return result

    def _extract(self, label):
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, self.data.replace("\n", " "))
        return match.group(2).strip() if match else "unbekannt"
