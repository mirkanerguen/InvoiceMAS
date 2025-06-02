# supervisor_agent.py
import json
import re
from langchain_community.llms import Ollama
from agents.validation_agent import ValidationAgent
from agents.accounting_agent import AccountingAgent
from agents.approval_agent import ApprovalAgent
from agents.booking_agent import BookingAgent
from agents.check_agent import CheckAgent
from agents.archive_agent import ArchiveAgent
from config import RESULTS_PATH, OLLAMA_MODEL, WORKFLOW_STATUS_PATH

class SupervisorAgent:
    def __init__(self, pdf_path):
        # LLM und Pfad speichern
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.pdf_path = pdf_path

        # ValidationAgent vorbereiten
        self.validation_agent = ValidationAgent(pdf_path)
        self.results = {}

        # Workflow-Status laden
        self.workflow = self.load_workflow_status()

        # Reihenfolge der Agenten im Workflow
        self.steps = [
            ("validation", lambda: self.validation_agent.run()),
            ("accounting", lambda: AccountingAgent(RESULTS_PATH).action()),
            ("check", lambda: CheckAgent(RESULTS_PATH).action()),
            ("approval", lambda: ApprovalAgent(RESULTS_PATH).run()),
            ("booking", lambda: BookingAgent(RESULTS_PATH).action()),
            ("archiving", lambda: ArchiveAgent(RESULTS_PATH, self.pdf_path).action())
        ]

    def load_workflow_status(self):
        # Lade aktuellen Status des Workflows (z. B. grün, gelb, rot)
        with open(WORKFLOW_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_workflow_status(self):
        # Speichere den Workflow-Status zurück ins JSON
        with open(WORKFLOW_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.workflow, f, indent=4)

    def save_results(self, step, result):
        # Zwischenergebnisse in results.json sichern
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                self.results = json.load(f)
        except FileNotFoundError:
            self.results = {}

        self.results[step] = result

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)

    def step_to_key(self, step_name):
        # Übersetzt Schrittname in Key des Workflow-Status
        mapping = {
            "validation": "1_validation",
            "accounting": "2_accounting",
            "check": "3_check",
            "approval": "4_approval",
            "booking": "5_booking",
            "archiving": "6_archiving"
        }
        return mapping.get(step_name, step_name)

    def extract_missing_fields(self, validation_text: str) -> list:
        # Extrahiert alle Pflichtfelder (1–10), die fehlen oder auf "Nein" stehen
        pattern = r"\|\s*(\d+\..*?)\s*\|\s*(Nein|Fehlt)\s*\|"
        matches = re.findall(pattern, validation_text)
        return [feld for feld, status in matches if feld.strip().startswith(tuple(f"{i}." for i in range(1, 11)))]

    def rerun_validation_for_missing(self, fehlende_felder: list) -> str:
        # Führt den ValidationAgent gezielt nochmal aus mit nur den fehlenden Feldern
        print("SupervisorAgent: Starte gezielte Nachprüfung im ValidationAgent.")
        agent = ValidationAgent(self.pdf_path)
        return agent.run(missing_fields=fehlende_felder)

    def merge_validation_results(self, original: str, improved: str) -> str:
        # Kombiniert alte Tabelle mit neu extrahierten Feldern (ersetzt fehlende Einträge)
        original_lines = original.splitlines()
        improved_lines = improved.splitlines()
        updated = []
        for o_line in original_lines:
            if "| Nein | -" in o_line or "| Fehlt | -" in o_line:
                key = o_line.split("|")[1].strip()
                match = next((l for l in improved_lines if key in l and "| Ja" in l), None)
                updated.append(match if match else o_line)
            else:
                updated.append(o_line)
        return "\n".join(updated)

    def think(self, agent_result, step):
        # LLM-Evaluation: Prüfe, ob der Agent alles korrekt geliefert hat
        prompt = (
            f"Du prüfst den Schritt '{step}'. Ergebnis: {agent_result}. "
            "Ist das Ergebnis vollständig und korrekt nach §14 UStG? Antworte nur mit 'ja' oder 'nein' "
            "und nenne, was fehlt, falls 'nein'."
        )
        return self.llm.invoke(prompt).strip().lower()

    def run_agent_and_validate(self, step, agent_fn):
        print(f"SupervisorAgent: Starte {step}-Agent.")
        result = agent_fn()
        self.save_results(step, result)

        # Nachlauf-Logik: Validation mit Pflichtfeldprüfung
        if step == "validation":
            fehlende_felder = self.extract_missing_fields(result)
            if fehlende_felder:
                print(f"SupervisorAgent: Fehlende Pflichtangaben erkannt: {fehlende_felder}")
                improved_result = self.rerun_validation_for_missing(fehlende_felder)
                result = self.merge_validation_results(result, improved_result)
                self.save_results(step, result)

        # Nachlauf-Logik: Genehmigung – falls verweigert → Workflowabbruch
        if step == "approval":
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("approval_status") == "verweigert":
                self.workflow[self.step_to_key(step)] = 3
                self.save_workflow_status()
                return "Abbruch durch Genehmigung."
            else:
                self.workflow[self.step_to_key(step)] = 2
                self.save_workflow_status()
                return result

        # Accounting = immer Status 2
        if step == "accounting":
            self.workflow[self.step_to_key(step)] = 2
            self.save_workflow_status()
            return result

        # CheckAgent: Bei "nicht nachvollziehbar" → Nutzer entscheidet
        if step == "check":
            if self.results.get("check") == "nicht_nachvollziehbar":
                user_decision = input("Sachliche Prüfung nicht nachvollziehbar. Trotzdem fortfahren? (ja/nein): ").strip().lower()
                if user_decision != "ja":
                    self.workflow[self.step_to_key(step)] = 3
                    self.save_workflow_status()
                    return "Abbruch durch Check."
                else:
                    self.workflow[self.step_to_key(step)] = 2
                    self.save_workflow_status()
                    return result
            else:
                self.workflow[self.step_to_key(step)] = 2
                self.save_workflow_status()
                return result

        # Für alle übrigen Schritte: LLM evaluiert ob Ergebnis okay war
        thought = self.think(result, step)
        if "nein" in thought:
            self.workflow[self.step_to_key(step)] = 1
        else:
            self.workflow[self.step_to_key(step)] = 2

        self.save_workflow_status()
        return result

    def next_step(self):
        # Führt den nächsten fälligen Schritt im Workflow aus
        if any(v == 3 for v in self.workflow.values()):
            return "Abbruch"

        for i, (step, agent_fn) in enumerate(self.steps):
            key = f"{i+1}_{step}"
            status = self.workflow.get(key, 0)

            if status == 2:
                continue
            if status == 3:
                return "Abbruch"

            print(f"SupervisorAgent: Ausführung von Schritt '{step}' begonnen.")
            result = self.run_agent_and_validate(step, agent_fn)
            if isinstance(result, str) and "Abbruch" in result:
                return result
            return f"Schritt '{step}' erfolgreich durchgeführt."

        return "Done"

    def action(self):
        # Hauptmethode: führt alle Schritte in Schleife aus, bis "Done" oder Fehler
        while True:
            result = self.next_step()
            if result == "Done" or "Abbruch" in result:
                return result
