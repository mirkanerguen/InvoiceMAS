import json
from langchain_community.llms import Ollama
from utils.login import check_credentials
import re

class ApprovalAgent:
    def __init__(self, result_path="data/intermediate_results.json"):
        self.llm = Ollama(model="mistral")
        with open(result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.validation_text = self.data.get("validation", "")

    def goal(self):
        return "Entscheide, ob die Rechnung auf Basis des Betrags genehmigt werden darf. Authentifiziere ggf. den verantwortlichen Mitarbeiter."

    def prompt(self, invoice_text):
        return f"""
Du bist ein Freigabe-Agent für Rechnungen.

Du erhältst einen strukturierten Rechnungsauszug mit allen Pflichtangaben (§14 UStG).
Extrahiere den Netto-Betrag und entscheide, welche Rolle für die Genehmigung zuständig ist:
- Bis 500 €: Mitarbeiter
- Bis 5.000 €: Teamleiter
- Über 5.000 €: Abteilungsleiter

Strukturiere deine Antwort so:
1. Extrahierter Netto-Betrag: [Betrag]
2. Verantwortliche Rolle: [Rolle]

Rechnungsauszug:
{invoice_text}
"""

    def think(self):
        print("ApprovalAgent Think(): Prüfe, wie hoch der Betrag ist und welche Rolle freigeben darf.")
        formatted_prompt = self.prompt(self.validation_text)
        response = self.llm.invoke(formatted_prompt)
        print("ApprovalAgent LLM-Antwort:", response)
        return response

    def action(self, decision_text):
        match = re.search(r"Betrag:\s*([\d.,]+)", decision_text)
        amount = float(match.group(1).replace(".", "").replace(",", ".")) if match else 0.0

        # Entscheidung basierend auf Betrag
        if amount <= 500:
            return "✅ Genehmigt – Rolle: Mitarbeiter"
        elif amount <= 5000:
            username = input("Login Teamleiter – Benutzername: ")
            password = input("Passwort: ")
            if check_credentials(username, password):
                return "✅ Genehmigt – Rolle: Teamleiter"
            else:
                return "❌ Login fehlgeschlagen. Genehmigung verweigert."
        else:
            username = input("Login Abteilungsleiter – Benutzername: ")
            password = input("Passwort: ")
            if check_credentials(username, password):
                return "✅ Genehmigt – Rolle: Abteilungsleiter"
            else:
                return "❌ Login fehlgeschlagen. Genehmigung verweigert."

    def run(self):
        thoughts = self.think()
        return self.action(thoughts)
