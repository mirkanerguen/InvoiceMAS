import json
from langchain_community.llms import Ollama
from agents.validation_agent import ValidationAgent
from agents.accounting_agent import AccountingAgent
from agents.approval_agent import ApprovalAgent
from agents.booking_agent import BookingAgent
from agents.check_agent import CheckAgent
from agents.archive_agent import ArchiveAgent
from config import RESULTS_PATH, OLLAMA_MODEL

class SupervisorAgent:
    def __init__(self, pdf_path):
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.pdf_path = pdf_path
        self.validation_agent = ValidationAgent(pdf_path)
        self.results = {}

    def goal(self):
        return ("Der Supervisor-Agent steuert den Rechnungsfreigabe-Workflow. "
                "Er prüft Ergebnisse der Worker-Agenten, erkennt eigenständig Fehler, "
                "und verbessert automatisch Instruktionen per sv_prompt().")

    def prompt(self):
        return ("Du bist der Supervisor-Agent im MAS. "
                "Deine Aufgabe: Steuerung der Worker-Agenten Validation → Accounting → Approval. "
                "Überprüfe die Ergebnisse sorgfältig auf Vollständigkeit und logische Konsistenz.")

    def think(self, agent_result, step):
        thought_prompt = (
            f"Du prüfst gerade den Schritt: {step}. Ergebnis: {agent_result}. "
            "Ist das Ergebnis vollständig und logisch korrekt gemäß §14 UStG? "
            "Antwort nur mit 'ja' oder 'nein' und gib kurz an, was fehlt, wenn nein."
        )
        thought = self.llm.invoke(thought_prompt).strip().lower()
        return thought

    def action(self):

        # 1. Validation
        print("SupervisorAgent: Starte Validation-Agent.")
        validation_result = self.validation_agent.run()
        self.save_intermediate_result("validation", validation_result)

        thought = self.think(validation_result, "Validation")
        if "nein" in thought:
            print("Fehler erkannt:", thought)
            # 1. Versuch automatische Korrektur
            improved_prompt = self.sv_prompt(validation_result, thought)
            validation_result = self.validation_agent.run(improved_prompt)
            self.save_intermediate_result("validation", validation_result)

            thought = self.think(validation_result, "Validation")
            if "nein" in thought:
                # 2. Versuch manuelle Ergänzung
                print("Wiederholt Fehler erkannt, Benutzerinteraktion nötig.")
                missing_info = self.ask_user(thought)
                validation_result = self.validation_agent.run_with_user_input(missing_info)
                self.save_intermediate_result("validation", validation_result)

        # 2. Accounting
        print("SupervisorAgent: Starte Accounting-Agent.")
        accounting_agent = AccountingAgent(RESULTS_PATH)
        cost_center = accounting_agent.action()
        self.save_intermediate_result("accounting", cost_center)

        # 3. Sachliche Prüfung
        print("SupervisorAgent: Starte Check-Agent (sachliche Prüfung).")
        check_agent = CheckAgent(RESULTS_PATH)
        check_result = check_agent.action()
        self.save_intermediate_result("check", check_result)

        # 4. Freigabe
        print("SupervisorAgent: Starte Approval-Agent.")
        approval_agent = ApprovalAgent(RESULTS_PATH)
        decision_text = approval_agent.think()
        approval_result = approval_agent.action(decision_text)

        # Lese nach dem internen Speichern im Agenten die Datei NEU
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            updated_results = json.load(f)

        approval_status = updated_results.get("approval_status", "")
        self.results = updated_results  # Optional: sync im Speicher aktualisieren
        self.save_intermediate_result("approval", approval_result)  # falls du auch approval_text nochmal mitschreiben willst

        if approval_status == "verweigert":
            print("SupervisorAgent: Genehmigung verweigert - Workflow wird gestoppt.")
            return approval_result


        # 5. Buchung
        print("SupervisorAgent: Starte Booking-Agent.")
        booking_agent = BookingAgent(RESULTS_PATH)
        booking_result = booking_agent.action()
        self.save_intermediate_result("booking", booking_result)

        booking_status = self.get_booking_status()
        if booking_status == "abgebrochen":
            print("SupervisorAgent: Rechnung bereits gebucht - Archivierung wird übersprungen.")
            return booking_result

        # 6. Archivierung
        print("SupervisorAgent: Starte Archivierungs-Agent.")
        archive_agent = ArchiveAgent(RESULTS_PATH, self.pdf_path)
        archive_result = archive_agent.action()
        self.save_intermediate_result("archive", archive_result)

        return archive_result

    def sv_prompt(self, previous_result, error_description):
        prompt = (
            f"Der vorherige Versuch hat Fehler produziert: {error_description}. "
            f"Bitte korrigiere diese Fehler nun. Das letzte Ergebnis war: {previous_result}."
        )
        improved_prompt = self.llm.invoke(prompt)
        print("Verbesserter Prompt generiert:", improved_prompt)
        return improved_prompt

    def ask_user(self, missing_info):
        user_input = input(f"Supervisor fragt: '{missing_info}'. Bitte geben Sie die fehlende Information ein: ")
        return user_input

    def save_intermediate_result(self, step, result):
        self.results[step] = result
        with open(RESULTS_PATH, "w", encoding="utf-8") as file:
            json.dump(self.results, file, indent=4)

    def get_booking_status(self):
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("booking_status", "")
