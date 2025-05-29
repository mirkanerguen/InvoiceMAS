import json
import re
from langchain_community.llms import Ollama
from config import (
    OLLAMA_MODEL,
    RESULTS_PATH,
    TEAMLEITER_ROLE,
    ABTEILUNGSLEITER_ROLE
)
from utils.login import check_credentials
from utils.approval_tool import map_bruttobetrag_to_role

class ApprovalAgent:
    def __init__(self, result_path=RESULTS_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.result_path = result_path

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.validation_text = self.data.get("validation", "")
        self.bruttobetrag = float(self.extract_bruttobetrag_with_llm(self.validation_text))

    def goal(self):
        return "Anhand des Bruttobetrags die richtige Genehmigungsrolle bestimmen."

    def prompt(self):
        return (
            "Genehmigungsregeln:\n"
            "- 1 = Mitarbeiter (bis 500 €)\n"
            "- 2 = Teamleiter (bis 5.000 €)\n"
            "- 3 = Abteilungsleiter (bis 20.000 €)\n"
            "- 4 = Manager (über 20.000 €)\n"
        )

    def think(self):
        gedanke = (
            f"Der Bruttobetrag der Rechnung beträgt {self.bruttobetrag:.2f} €. "
            "Daher ist zu prüfen, in welchen Bereich dieser Betrag fällt, um die passende Genehmigungsrolle zu ermitteln."
        )
        print("ApprovalAgent Think():", gedanke)
        return gedanke

    def extract_bruttobetrag_with_llm(self, validation_text: str) -> str:
        prompt = f"""
Du bist ein Genehmigungsassistent. Extrahiere aus folgendem Text den **Bruttobetrag/Gesamtbetrag der Rechnung** in Euro. 
Berücksichtige ausschließlich die Angabe aus Zeile 9 der Tabelle ("Entgelt nach Steuersätzen aufgeschlüsselt").

Text:
{validation_text}

Gib nur den Betrag in dieser Form zurück, z. B.: 2915.50
"""
        response = self.llm.invoke(prompt).strip()

        match = re.search(r"([\d]+[\.,]?[\d]*)", response)
        if match:
            betrag = match.group(1).replace(",", ".")
            try:
                return betrag
            except ValueError:
                pass
        return "0.00"

    def action(self):
        entscheidung = map_bruttobetrag_to_role(self.bruttobetrag)
        result = "Unbekannter Entscheidungswert"
        status = "offen"

        if entscheidung == "1":
            result = "Genehmigt - Rolle: Mitarbeiter"
            status = "genehmigt"

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

        elif entscheidung == "0":
            result = "Genehmigung verweigert"
            status = "verweigert"

        self.data["approval"] = result
        self.data["approval_status"] = status

        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        print("ApprovalAgent: Entscheidung gespeichert.")
        return result

    def run(self):
        self.think()
        return self.action()
