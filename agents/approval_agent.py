import json
import re
from langchain_ollama import OllamaLLM
from config import (
    OLLAMA_MODEL,
    RESULTS_PATH,
    TEAMLEITER_ROLE,
    ABTEILUNGSLEITER_ROLE,
    OLLAMA_BASE_URL
)
from utils.login import check_credentials
from utils.approval_tool import map_bruttobetrag_to_role

class ApprovalAgent:
    def __init__(self, result_path=RESULTS_PATH):
        # Initialisiere LLM und lade das results.json
        self.llm = OllamaLLM(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL
)

        self.result_path = result_path

        # Lade vorhandene Ergebnisse aus der Datei
        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Speichere den extrahierten Validation-Text
        self.validation_text = self.data.get("validation", "")
        # Extrahiere Bruttobetrag (als Float), z. B. für Genehmigungsentscheidung
        self.bruttobetrag = float(self.extract_bruttobetrag_with_llm(self.validation_text))

    def goal(self):
        # Zieldefinition für Agenten
        return "Anhand des Bruttobetrags die richtige Genehmigungsrolle bestimmen."

    def prompt(self):
        # Überblick über Genehmigungsregeln (zur Referenz oder Prompt-Nutzung)
        return (
            "Genehmigungsregeln:\n"
            "- 1 = Mitarbeiter (bis 500 €)\n"
            "- 2 = Teamleiter (bis 5.000 €)\n"
            "- 3 = Abteilungsleiter (bis 20.000 €)\n"
            "- 4 = Manager (über 20.000 €)\n"
        )

    def think(self):
        # Gedankenformulierung zur internen Begründung der Entscheidung
        gedanke = (
            f"Der Bruttobetrag der Rechnung beträgt {self.bruttobetrag:.2f} €. "
            "Daher ist zu prüfen, in welchen Bereich dieser Betrag fällt, um die passende Genehmigungsrolle zu ermitteln."
        )
        print("ApprovalAgent Think():", gedanke)
        return gedanke

    def extract_bruttobetrag_with_llm(self, validation_text: str) -> str:
        # Extrahiere den Bruttobetrag aus dem Validation-Feld mit Hilfe eines LLM
        prompt = f"""
Du bist ein Genehmigungsassistent. Extrahiere aus folgendem Text den **Bruttobetrag/Gesamtbetrag der Rechnung** in Euro. 
Berücksichtige ausschließlich die Angabe aus Zeile 9 der Tabelle ("Entgelt nach Steuersätzen aufgeschlüsselt").

Text:
{validation_text}

Gib nur den Betrag in dieser Form zurück, z. B.: 2915.50
"""
        response = self.llm.invoke(prompt).strip()

        # Versuche, Betrag mit Regex zu extrahieren und in Float zu parsen
        match = re.search(r"([\d]+[\.,]?[\d]*)", response)
        if match:
            betrag = match.group(1).replace(",", ".")
            try:
                return betrag
            except ValueError:
                pass
        return "0.00"

    def action(self):
        # Bruttobetrag klassifizieren → Rolle bestimmen
        entscheidung = map_bruttobetrag_to_role(self.bruttobetrag)
        result = "Unbekannter Entscheidungswert"
        status = "offen"

        # Automatisch genehmigen bei "Mitarbeiter" (bis 500 €)
        if entscheidung == "1":
            result = "Genehmigt - Rolle: Mitarbeiter"
            status = "genehmigt"

        # Teamleiter-Login (bis 5.000 €)
        elif entscheidung == "2":
            print(f"Login {TEAMLEITER_ROLE}:")
            username = input("Benutzername: ")
            password = input("Passwort: ")
            if check_credentials(username, password, role=TEAMLEITER_ROLE):
                result = f"Genehmigt - Rolle: {TEAMLEITER_ROLE}"
                status = "genehmigt"
            else:
                result = "Login fehlgeschlagen - Genehmigung verweigert"
                status = "verweigert"

        # Abteilungsleiter-Login (bis 20.000 €)
        elif entscheidung == "3":
            print(f"Login {ABTEILUNGSLEITER_ROLE}:")
            username = input("Benutzername: ")
            password = input("Passwort: ")
            if check_credentials(username, password, role=ABTEILUNGSLEITER_ROLE):
                result = f"Genehmigt - Rolle: {ABTEILUNGSLEITER_ROLE}"
                status = "genehmigt"
            else:
                result = "Login fehlgeschlagen - Genehmigung verweigert"
                status = "verweigert"

        # 0 = explizite Ablehnung (z. B. fehlerhafter Betrag oder keine Regel erfüllt)
        elif entscheidung == "0":
            result = "Genehmigung verweigert"
            status = "verweigert"

        # Ergebnis in results.json speichern
        self.data["approval"] = result
        self.data["approval_status"] = status

        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        print("ApprovalAgent: Entscheidung gespeichert.")
        return result

    def run(self):
        # Führt den vollständigen Ablauf durch (Gedanke + Entscheidung)
        self.think()
        return self.action()
