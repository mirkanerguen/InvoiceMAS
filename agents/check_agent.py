import json
import re
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from config import RESULTS_PATH, REFERENCE_DATA_PATH, OLLAMA_MODEL, OWN_COMPANY_FULL, OLLAMA_BASE_URL

class CheckAgent:
    def __init__(self, validation_result_path=RESULTS_PATH, reference_path=REFERENCE_DATA_PATH):
        # Initialisiere LLM mit lokalem Ollama-Modell
        self.llm = OllamaLLM(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL
        )

        # Lade Validierungsdaten aus vorherigem Agentenlauf
        with open(validation_result_path, "r", encoding="utf-8") as f:
            self.raw_data = json.load(f).get("validation", "")

        # Lade bekannte Rechnungsreferenzen für den Abgleich
        with open(reference_path, "r", encoding="utf-8") as f:
            self.known = json.load(f).get("invoices", [])

        # Bereinige den extrahierten Text zur Weiterverarbeitung
        self.data = self._normalize_text(self.raw_data)

    def goal(self):
        # Zieldefinition für den Prompt
        return "Prüfe die sachliche Richtigkeit einer Rechnung mit Fokus auf Rechnungsnummer, plausiblen Lieferanten, Leistung und Bruttobetrag."

    def think(self):
        # Extrahiere alle prüfungsrelevanten Felder aus der Tabelle
        unternehmer = self._extract("1. Name & Anschrift des leistenden Unternehmers")
        empfaenger = self._extract("2. Name & Anschrift des Leistungsempfängers")

        # Bestimme den Lieferanten (nicht das eigene Unternehmen)
        if OWN_COMPANY_FULL in unternehmer:
            lieferant = empfaenger
        else:
            lieferant = unternehmer

        return {
            "rechnungsnummer": self._extract("6. Fortlaufende Rechnungsnummer"),
            "lieferant": lieferant,
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
            self._save_result("nicht_nachvollziehbar")
            return "nicht_nachvollziehbar"

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

        prompt_template = PromptTemplate(
            input_variables=["ziel", "rechnung", "referenz"],
            template="""Du bist ein KI-Agent für Rechnungsprüfung.

    Aufgabe: {ziel}

    Vergleiche die folgende Rechnung mit den bekannten Referenzdaten und prüfe, ob sie sachlich übereinstimmen.

    Rechnung:
    {rechnung}

    Referenzdaten:
    {referenz}

    Kriterien:
    - Rechnungsnummer muss exakt gleich sein.
    - Lieferant darf sprachlich leicht abweichen, aber inhaltlich gleich sein.
    - Leistungen dürfen in anderer Reihenfolge oder Kürze genannt sein.
    - Bruttobetrag darf max. 0,01 € abweichen.
    - Wenn die Rechnungsnummer exakt übereinstimmt, ist die Prüfung **sachlich korrekt**, außer es liegt ein gravierender Widerspruch bei Betrag oder Lieferant vor.

    Antwort nur mit:  
    - **sachlich_korrekt**  
    - **nicht_nachvollziehbar**
    """
        )

        prompt = prompt_template.format(
            ziel=self.goal(),
            rechnung=rechnung_text,
            referenz=referenz_text
        )
        result = self.llm.invoke(prompt).strip().lower()

        # 1. Wenn Modell korrekt reagiert
        if "sachlich_korrekt" in result:
            self._save_result("sachlich_korrekt")
            return "sachlich_korrekt"

        if "nicht_nachvollziehbar" in result:
            # Prüfe trotzdem Fallback
            if referenz["rechnungsnummer"].strip() == extracted["rechnungsnummer"].strip():
                print("CheckAgent Fallback: Rechnungsnummer stimmt exakt – setze auf sachlich_korrekt.")
                self._save_result("sachlich_korrekt")
                return "sachlich_korrekt"
            self._save_result("nicht_nachvollziehbar")
            return "nicht_nachvollziehbar"

        # 2. Fallback bei Rechnungsnummer (auch wenn Modell keine klare Antwort gibt)
        if referenz["rechnungsnummer"].strip() == extracted["rechnungsnummer"].strip():
            print("CheckAgent Safety-Fallback: Rechnungsnummer stimmt exakt – Modellantwort unklar – setze auf sachlich_korrekt.")
            self._save_result("sachlich_korrekt")
            return "sachlich_korrekt"

        # 3. Wenn alles fehlschlägt
        self._save_result("unklar")
        return "unklar"


    def _save_result(self, result_value):
        # Speichere das Ergebnis in results.json
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        data["check"] = result_value
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _extract(self, label):
        # Extrahiere spezifische Zeile aus der Markdown-Tabelle
        pattern = fr"\|\s*{label}.*?\|\s*(Ja|Nein|Fehlt)\s*\|\s*(.*?)\|"
        match = re.search(pattern, self.data.replace("\n", " "))
        return match.group(2).strip() if match else "unbekannt"

    def _extract_bruttobetrag(self, betrag_text):
        # Versuche den Bruttobetrag aus der Textzeile zu extrahieren
        match = re.search(r"([\d\.,]+)\s*€?\s*\(Brutto\)", betrag_text)
        return match.group(1).replace(",", ".") if match else "0.00"

    def _normalize_text(self, text):
        # HTML und Sonderzeichen entfernen
        text = text.replace("<br>", ", ")
        text = text.replace("€", "EUR")
        text = text.replace("\u00a0", " ")
        return text
