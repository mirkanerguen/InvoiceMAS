import json
from langchain_community.llms import Ollama
from utils.login import check_credentials
from config import OLLAMA_MODEL, RESULTS_PATH, TEAMLEITER_ROLE, ABTEILUNGSLEITER_ROLE

class ApprovalAgent:
    def __init__(self, result_path=RESULTS_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)
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

Lies dir den folgenden strukturierten Rechnungsauszug durch und gib **ausschließlich eine Zahl (0-3)** zurück, die deine Entscheidung darstellt:

1 = Genehmigung durch Mitarbeiter (bis 500 €)  
2 = Genehmigung durch Teamleiter (501-5.000 €)  
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
            result = "Genehmigt - Rolle: Mitarbeiter"
            status = "genehmigt"
            self.data["expected_role"] = "employee"

        elif decision_code == "2":
            result = "Genehmigt - Rolle: Teamleiter"
            status = "genehmigt"
            self.data["expected_role"] = TEAMLEITER_ROLE  # "teamlead"

        elif decision_code == "3":
            result = "Genehmigt - Rolle: Abteilungsleiter"
            status = "genehmigt"
            self.data["expected_role"] = ABTEILUNGSLEITER_ROLE  # "departmentlead"

        elif decision_code == "0":
            result = "Genehmigung verweigert"
            status = "verweigert"

        self._save_result(result, status)
        return result

    def _save_result(self, result, status, user=None, amount=None):
        self.data["approval"] = result
        self.data["approval_status"] = status
        if user:
            self.data["approved_by"] = user
        if amount:
            self.data["approved_amount"] = amount
        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
        print("ApprovalAgent: Entscheidung gespeichert.")


    def run(self):
        decision = self.think()
        return self.action(decision)
