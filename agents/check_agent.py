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

        # Referenzdaten vorbereiten
        referenzliste = "\n".join([
            f"- Rechnungsnr: {ref['rechnungsnummer']}, Lieferant: {ref['lieferant']}, Leistung: {ref['leistung']}, Brutto: {ref['betrag_brutto']} €"
            for ref in self.known
        ])

        # Betrag extrahieren
        brutto_match = re.search(r"Brutto[: ]*([\d\.,]+)", extracted["betrag"])
        brutto = brutto_match.group(1) if brutto_match else "unbekannt"

        # Rechnungstext zusammensetzen
        rechnung_text = (
            f"Rechnungsnummer: {extracted['rechnungsnummer']}\n"
            f"Lieferant: {extracted['lieferant']}\n"
            f"Leistung: {extracted['leistung']}\n"
            f"Brutto-Betrag: {brutto} €"
        )

        prompt_template = PromptTemplate(
        input_variables=["ziel", "rechnung", "referenzen"],
        template="""Du bist ein KI-Agent zur sachlichen Prüfung von Rechnungen.

    Dein Ziel lautet: {ziel}

    Gegeben ist die extrahierte Rechnung:
    {rechnung}

    Und hier sind bekannte interne Referenzrechnungen:
    {referenzen}

    Führe folgenden Abgleich durch:

    1. **Rechnungsnummer**: Die Nummer muss **exakt** mit einer bekannten übereinstimmen. Wenn nicht, gilt die Prüfung als **nicht nachvollziehbar**.
    2. **Lieferant, Leistung und Bruttobetrag**: Diese sollen zusätzlich plausibel übereinstimmen (auch sinngemäß).

    Antworte am Ende ausschließlich mit einem dieser Begriffe:
    - sachlich_korrekt (wenn alle Kriterien erfüllt sind, inklusive Rechnungsnummer)
    - nicht_nachvollziehbar (wenn die Rechnungsnummer abweicht oder die Daten nicht plausibel sind)
    """
    )


        prompt = prompt_template.format(
            ziel=self.goal(),
            rechnung=rechnung_text,
            referenzen=referenzliste
        )

        # KI-Bewertung einholen
        result = self.llm.invoke(prompt).strip().lower()

        if result == "sachlich_korrekt":
            print("CheckAgent Action(): sachlich korrekt")
            return "sachlich_korrekt"
        elif result == "nicht_nachvollziehbar":
            print("CheckAgent Action(): nicht nachvollziehbar")
            return "nicht_nachvollziehbar"
        else:
            print("CheckAgent Action(): unklar – keine eindeutige KI-Antwort erhalten.")
            return "unklar"

    def _extract(self, label):
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, self.data.replace("\n", " "))
        return match.group(2).strip() if match else "unbekannt"
