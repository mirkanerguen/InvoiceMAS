import json
import re
from langchain_community.llms import Ollama
from config import RESULTS_PATH, CREDENTIALS_PATH, OLLAMA_MODEL
from utils.approval_rules import APPROVAL_RULES

class ApprovalAgent:
    def __init__(self, result_path=RESULTS_PATH):
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.result_path = result_path

        with open(self.result_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.validation_text = self.data.get("validation", "")

    def goal(self):
        return "Bestimme anhand des Bruttobetrags die benötigte Genehmigungsrolle und führe einen Login entsprechend durch."

    def prompt(self):
        return f"""
Du bist ein intelligenter Approval-Agent.

Dein Ziel: Extrahiere den Bruttobetrag aus folgender Rechnung.
Antworte nur mit einer Zahl (Beispiel: 2915.50)

Rechnungsdaten:
{self.validation_text}
"""

    def think(self):
        print("ApprovalAgent Think(): Bruttobetrag wird per LLM extrahiert...")
        response = self.llm.invoke(self.prompt()).strip()
        try:
            betrag = float(response.replace(",", "."))
            print(f"Extrahierter Betrag: {betrag}")
            return betrag
        except ValueError:
            print("[WARNUNG] Betrag konnte nicht interpretiert werden:", response)
            return 0.0

    def get_required_role(self, betrag):
        for role, limit in APPROVAL_RULES.items():
            if betrag <= limit:
                return role
        return "manager"

    def login_prompt(self, role):
        return f"""
Du bist nun im Login-Modus.

Genehmigung erforderlich durch: {self._display_role(role)}

Bitte gib Benutzername und Passwort ein.
"""

    def _display_role(self, role):
        return {
            "employee": "Mitarbeiter",
            "teamlead": "Teamleiter",
            "departmentlead": "Abteilungsleiter",
            "manager": "Manager"
        }.get(role, role)

    def validate_login(self, username, password, expected_role):
        try:
            with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
                users = json.load(f).get("users", [])
        except Exception as e:
            print(f"Fehler beim Laden der Login-Daten: {e}")
            return False

        for user in users:
            if user.get("username") == username and user.get("password") == password:
                print(f"[DEBUG] Login akzeptiert ({username})")
                return True
        print("[DEBUG] Login fehlgeschlagen.")
        return False

    def action(self):
        betrag = self.think()
        role = self.get_required_role(betrag)
        self.data["expected_role"] = role
        self.data["approval_amount"] = betrag

        # Simulierter Login (z. B. durch UI)
        print(self.login_prompt(role))
        username = input("Benutzername: ")
        password = input("Passwort: ")

        if self.validate_login(username, password, role):
            result = f"Genehmigt - Rolle: {self._display_role(role)}"
            status = "genehmigt"
            self.data["approval"] = result
            self.data["approval_status"] = status
            self.data["approved_by"] = username
            print("ApprovalAgent: Genehmigung erfolgreich.")
        else:
            result = "Genehmigung verweigert"
            status = "verweigert"
            self.data["approval"] = result
            self.data["approval_status"] = status
            print("ApprovalAgent: Genehmigung verweigert.")

        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        return self.data["approval"]
