import json
import re
from config import RESULTS_PATH
from utils.cost_center import COST_CENTER_RULES, DEFAULT_COST_CENTER
from langchain_community.llms import Ollama

class AccountingAgent:
    def __init__(self, result_path=RESULTS_PATH):
        self.path = result_path
        self.llm = Ollama(model="mistral")
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def goal(self):
        return "Ordne der Rechnung eine passende Kostenstelle zu."

    def prompt(self):
        leistung = self._get_leistung()
        return f"""
Du bist ein Accounting-Agent.

Ordne basierend auf folgender Leistungsbeschreibung eine passende Kostenstelle zu.

Leistung: {leistung}

Bekannte Kostenstellen:
- 1001-Beratung
- 1002-IT
- 1003-Marketing
- 1004-Beschaffung
- 1005-Personal
- 1099-Sonstiges

Gib **nur** die Kostenstelle zurück (z. B. 1003-Marketing).
"""

    def _get_leistung(self):
        try:
            table = self.data.get("validation", "")
            for line in table.splitlines():
                if "7." in line:
                    return line.split("|")[-1].strip()
        except Exception as e:
            print("[AccountingAgent] Fehler bei Leistungs-Extraktion:", e)
        return ""

    def think(self):
        return "Ich prüfe die Leistungsbeschreibung und suche nach bekannten Schlüsselbegriffen."

    def rule_based_assignment(self, text):
        text_lower = text.lower()
        for keyword, kostenstelle in COST_CENTER_RULES.items():
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                return kostenstelle
        return None

    def action(self):
        print("AccountingAgent Think():", self.think())
        leistung = self._get_leistung()

        kostenstelle = self.rule_based_assignment(leistung)
        if kostenstelle:
            print(f"Rule-Based Match gefunden: {kostenstelle}")
        else:
            print("Kein Regel-Match. Fallback auf LLM.")
            kostenstelle = self.llm.invoke(self.prompt()).strip()
            if not kostenstelle:
                kostenstelle = DEFAULT_COST_CENTER

        self.data["accounting"] = kostenstelle
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

        print(f"AccountingAgent Action(): {kostenstelle}")
        return kostenstelle
