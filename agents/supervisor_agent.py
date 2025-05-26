import json
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
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.pdf_path = pdf_path
        self.validation_agent = ValidationAgent(pdf_path)
        self.results = {}
        self.workflow = self.load_workflow_status()

    def load_workflow_status(self):
        with open(WORKFLOW_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_workflow_status(self):
        with open(WORKFLOW_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.workflow, f, indent=4)

    def goal(self):
        return ("Supervisor-Agent steuert den Rechnungsworkflow anhand workflow_status.json. "
                "Er erkennt eigenständig den nächsten Schritt und prüft Ergebnisse per LLM.")

    def prompt(self):
        return ("Steuere die Reihenfolge der Agenten. Überprüfe Ergebnisse, erkenne Lücken "
                "und steuere gegebenenfalls die Nachbearbeitung.")

    def think(self, agent_result, step):
        prompt = (
            f"Du prüfst den Schritt '{step}'. Ergebnis: {agent_result}. "
            "Ist das Ergebnis vollständig und korrekt nach §14 UStG? Antworte nur mit 'ja' oder 'nein' "
            "und nenne, was fehlt, falls 'nein'."
        )
        response = self.llm.invoke(prompt).strip().lower()
        return response

    def run_agent_and_validate(self, step, agent_fn):
        print(f"SupervisorAgent: Starte {step}-Agent.")
        result = agent_fn()
        self.save_results(step, result)

        thought = self.think(result, step)
        if "nein" in thought:
            print(f"{step}-Ergebnis unvollständig: {thought}")
            self.workflow[f"{self.step_to_key(step)}"] = 1  # Gelb
        else:
            print(f"{step}-Ergebnis vollständig.")
            self.workflow[f"{self.step_to_key(step)}"] = 2  # Grün
        self.save_workflow_status()

    def action(self):
        steps = [
            ("validation", lambda: self.validation_agent.run()),
            ("accounting", lambda: AccountingAgent(RESULTS_PATH).action()),
            ("check", lambda: CheckAgent(RESULTS_PATH).action()),
            ("approval", lambda: ApprovalAgent(RESULTS_PATH).run()),
            ("booking", lambda: BookingAgent(RESULTS_PATH).action()),
            ("archiving", lambda: ArchiveAgent(RESULTS_PATH, self.pdf_path).action())
        ]

        for i, (step, agent_fn) in enumerate(steps):
            key = f"{i+1}_{step}"
            status = self.workflow.get(key, 0)

            if status == 2:
                continue  # Schritt bereits abgeschlossen
            elif status == 1:
                print(f"SupervisorAgent: Wiederhole {step}-Agent wegen gelbem Status.")
            elif status == 0:
                print(f"SupervisorAgent: {step}-Agent steht an.")

            self.run_agent_and_validate(step, agent_fn)

            if step == "check" and self.results.get("check") == "nicht_nachvollziehbar":
                user_decision = input("Sachliche Prüfung nicht nachvollziehbar. Trotzdem fortfahren? (ja/nein): ").strip().lower()
                if user_decision != "ja":
                    print("SupervisorAgent: Workflow abgebrochen durch den Nutzer.")
                    return "Abbruch durch Benutzer nach Check."

            # ⬅️ NACH EINEM SCHRITT direkt zurückkehren
            return f"{step} abgeschlossen."

        return "Workflow abgeschlossen."



    def save_results(self, step, result):
        self.results[step] = result
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)

    def step_to_key(self, step_name):
        mapping = {
            "validation": "1_validation",
            "accounting": "2_accounting",
            "check": "3_check",
            "approval": "4_approval",
            "booking": "5_booking",
            "archiving": "6_archiving"
        }
        return mapping.get(step_name, step_name)
