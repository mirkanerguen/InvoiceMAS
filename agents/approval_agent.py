import json
import re
from langchain_community.llms import Ollama
from utils.login import check_credentials

class ApprovalAgent:
    def __init__(self, result_path="data/results.json"):
        self.llm = Ollama(model="mistral")
        self.result_path = result_path
        with open(result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.validation_text = self.data.get("validation", "")

    def goal(self):
        return "Entscheide, ob die Rechnung basierend auf dem Bruttobetrag genehmigt werden darf. Authentifiziere ggf. die verantwortliche Person."

    def prompt(self, invoice_text):
        return f"""
Du bist ein Freigabe-Agent für eingehende Rechnungen.

Du erhältst einen strukturierten Rechnungsauszug.
Analysiere den Bruttobetrag und bestimme, wer die Genehmigung erteilen muss:

- Bis 500 €: Mitarbeiter
- Bis 5.000 €: Teamleiter
- Über 5.000 €: Abteilungsleiter

Antwortformat:
1. Bruttobetrag: [Betrag]
2. Zuständige Rolle: [Rolle]

Rechnungsauszug:
{invoice_text}
"""

    def think(self):
        print("ApprovalAgent Think(): Prüfe Betrag und bestimme Rolle.")
        formatted_prompt = self.prompt(self.validation_text)
        response = self.llm.invoke(formatted_prompt)
        print("ApprovalAgent Antwort:", response)
        return response

    def action(self, decision_text):
        rolle_match = re.search(r"[Zz]uständige[r]? Rolle[: ]*(\w+)", decision_text)
        betrag_match = re.search(r"[Bb]rutt[o]?-?[Bb]etrag[: ]*([\d.,]+)", decision_text)

        rolle = rolle_match.group(1).strip().lower() if rolle_match else "unbekannt"
        betrag = float(betrag_match.group(1).replace(".", "").replace(",", ".")) if betrag_match else 0.0

        if rolle == "mitarbeiter":
            result = "Genehmigt – Rolle: Mitarbeiter"

        elif rolle == "teamleiter":
            username = input("Login Teamleiter – Benutzername: ")
            password = input("Passwort: ")
            if check_credentials(username, password):
                result = "Genehmigt – Rolle: Teamleiter"
            else:
                result = "Login fehlgeschlagen – Genehmigung verweigert"

        elif rolle == "abteilungsleiter":
            username = input("Login Abteilungsleiter – Benutzername: ")
            password = input("Passwort: ")
            if check_credentials(username, password):
                result = "Genehmigt – Rolle: Abteilungsleiter"
            else:
                result = "Login fehlgeschlagen – Genehmigung verweigert"

        else:
            result = "Rolle konnte nicht zuverlässig ermittelt werden"

        # Ergebnis speichern
        self.data["approval"] = result
        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        return result

    def run(self):
        thoughts = self.think()
        return self.action(thoughts)
