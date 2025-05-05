import json
from langchain_community.llms import Ollama
from utils.login import check_credentials

class ApprovalAgent:
    def __init__(self, result_path="data/results.json"):
        self.llm = Ollama(model="mistral")
        self.result_path = result_path

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.validation_text = self.data.get("validation", "")

    def goal(self):
        return (
            "Bestimme anhand des Bruttobetrags in einer Rechnung, "
            "welche hierarchische Rolle (Mitarbeiter, Teamleiter, Abteilungsleiter) "
            "die Genehmigung erteilen muss. Entscheide selbstständig, ob eine Freigabe möglich ist."
        )

    def think(self):
        goal_text = self.goal()

        full_prompt = f"""
Du bist ein autonomer Freigabe-Agent.

Dein Ziel lautet:
„{goal_text}“

Lies dir den folgenden strukturierten Rechnungsauszug durch und gib **ausschließlich eine Zahl (0–3)** zurück, die deine Entscheidung darstellt:

1 = Genehmigung durch Mitarbeiter (bis 500 €)  
2 = Genehmigung durch Teamleiter (501–5.000 €)  
3 = Genehmigung durch Abteilungsleiter (ab 5.001 €)  
0 = Genehmigung verweigern

Rechnungsauszug:
{self.validation_text}

Antwort (nur Zahl): 
"""
        print("ApprovalAgent Think(): Ziel definiert und Prompt gesendet.")
        response = self.llm.invoke(full_prompt).strip()
        print("ApprovalAgent Entscheidung:", response)
        return response

    def action(self, decision_code):
        result = "Unbekannter Entscheidungswert"
        status = "offen"

        if decision_code == "1":
            result = "Genehmigt – Rolle: Mitarbeiter"
            status = "genehmigt"

        elif decision_code == "2":
            print("Login Teamleiter:")
            if check_credentials(input("Benutzername: "), input("Passwort: ")):
                result = "Genehmigt – Rolle: Teamleiter"
                status = "genehmigt"
            else:
                result = "Login fehlgeschlagen – Genehmigung verweigert"
                status = "verweigert"

        elif decision_code == "3":
            print("Login Abteilungsleiter:")
            if check_credentials(input("Benutzername: "), input("Passwort: ")):
                result = "Genehmigt – Rolle: Abteilungsleiter"
                status = "genehmigt"
            else:
                result = "Login fehlgeschlagen – Genehmigung verweigert"
                status = "verweigert"

        elif decision_code == "0":
            result = "Genehmigung verweigert"
            status = "verweigert"

        # Ergebnisse speichern
        self.data["approval"] = result
        self.data["approval_status"] = status

        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        print("ApprovalAgent: Entscheidung gespeichert.")
        return result

    def run(self):
        decision = self.think()
        return self.action(decision)
