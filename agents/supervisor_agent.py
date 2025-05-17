import json
from config import RESULTS_PATH
from langchain_community.llms import Ollama
from agents.validation_agent import ValidationAgent
from agents.accounting_agent import AccountingAgent
from agents.check_agent import CheckAgent
from agents.approval_agent import ApprovalAgent
from agents.booking_agent import BookingAgent
from agents.archive_agent import ArchiveAgent

class SupervisorAgent:
    def __init__(self, pdf_path):
        self.llm = Ollama(model="mistral")
        self.pdf_path = pdf_path
        self.results = {}

        # PDF-Pfad vorab in results.json speichern
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"pdf_path": pdf_path}, f, indent=4)

    def goal(self):
        return "Koordiniere alle Agenten im Workflow zur automatisierten Rechnungsfreigabe."

    def prompt(self):
        return (
            "Du bist der SupervisorAgent. Du führst den Agenten-Workflow in folgender Reihenfolge aus: "
            "Validation → Accounting → Check → Approval → Booking → Archive."
        )

    def think(self):
        return "Ich starte den validierten, sequentiellen Rechnungsfreigabeprozess."

    def action(self):
        print("SupervisorAgent Think():", self.think())

        # 1. Validation Agent
        print("SupervisorAgent: Starte Validation-Agent.")
        validation_agent = ValidationAgent(self.pdf_path)
        validation_result = validation_agent.action()
        self._save_step("validation", validation_result)

        # Prüfe auf fehlende Pflichtfelder 1–10
        missing = sum(1 for i in range(1, 11) if f"| {i}." in validation_result and "| Nein |" in validation_result)
        if missing > 0:
            print(f"Supervisor: {missing} Pflichtangaben fehlen. Validation-Agent wird erneut aufgerufen.")
            second_pass = validation_agent.action()
            combined = validation_result.strip() + "\n" + second_pass.strip()
            self._save_step("validation", combined)

        # 2. Accounting Agent
        print("SupervisorAgent: Starte Accounting-Agent.")
        accounting_agent = AccountingAgent(RESULTS_PATH)
        accounting_result = accounting_agent.action()
        self._save_step("accounting", accounting_result)

        # 3. Check Agent
        print("SupervisorAgent: Starte Check-Agent.")
        check_agent = CheckAgent(RESULTS_PATH)
        check_result = check_agent.action()
        self._save_step("check", check_result)

        if check_result in ["nicht_nachvollziehbar", "unklar"]:
            self.results["flag_wait_for_user_decision"] = True
            self._save_step("flag_wait_for_user_decision", True)
            print("SupervisorAgent: Benutzerentscheidung erforderlich. Pausiere.")
            return "Sachliche Entscheidung durch Benutzer erforderlich."

        # 4. Approval Agent
        print("SupervisorAgent: Starte Approval-Agent.")
        approval_agent = ApprovalAgent(RESULTS_PATH)
        approval_result = approval_agent.action()
        self._save_step("approval", approval_result)

        if self.results.get("approval_status") == "verweigert":
            print("SupervisorAgent: Genehmigung verweigert – Workflow abgebrochen.")
            return approval_result

        # 5. Booking Agent
        print("SupervisorAgent: Starte Booking-Agent.")
        booking_agent = BookingAgent(RESULTS_PATH)
        booking_result = booking_agent.action()
        self._save_step("booking", booking_result)

        if self.results.get("booking_status") == "abgebrochen":
            print("SupervisorAgent: Rechnung bereits gebucht – Archivierung wird übersprungen.")
            return booking_result

        # 6. Archive Agent
        print("SupervisorAgent: Starte Archivierungs-Agent.")
        archive_agent = ArchiveAgent(RESULTS_PATH)
        archive_result = archive_agent.action()
        self._save_step("archive", archive_result)

        return archive_result

    def _save_step(self, step, result):
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            self.results = json.load(f)
        self.results[step] = result
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)
