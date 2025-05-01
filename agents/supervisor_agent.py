from langchain_community.llms import Ollama
from agents.validation_agent import ValidationAgent
from agents.accounting_agent import AccountingAgent
import json

class SupervisorAgent:
    def __init__(self, pdf_path):
        self.llm = Ollama(model="mistral")
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
        thought_prompt = (f"Du prüfst gerade den Schritt: {step}. Ergebnis: {agent_result}. "
                          "Ist das Ergebnis vollständig und logisch korrekt gemäß §14 UStG? "
                          "Antwort nur mit 'ja' oder 'nein' und gib kurz an, was fehlt, wenn nein.")
        thought = self.llm.invoke(thought_prompt).strip().lower()
        return thought

    def action(self):
        print("SupervisorAgent: Starte Validation-Agent.")
        validation_result = self.validation_agent.run()
        self.save_intermediate_result('validation', validation_result)

        thought = self.think(validation_result, 'Validation')
        if 'nein' in thought:
            print("Fehler erkannt:", thought)
            # 1. Versuch der automatischen Korrektur
            improved_prompt = self.sv_prompt(validation_result, thought)
            validation_result = self.validation_agent.run(improved_prompt)
            self.save_intermediate_result('validation', validation_result)

            thought = self.think(validation_result, 'Validation')
            if 'nein' in thought:
                # 2. Versuch manuelle Korrektur
                print("Wiederholt Fehler erkannt, Benutzerinteraktion nötig.")
                missing_info = self.ask_user(thought)
                validation_result = self.validation_agent.run_with_user_input(missing_info)
                self.save_intermediate_result('validation', validation_result)

        # --- Hier erst Accounting-Agent starten ---
        print("SupervisorAgent: Starte Accounting-Agent.")
        accounting_agent = AccountingAgent("data/intermediate_results.json")
        cost_center = accounting_agent.action()
        self.save_intermediate_result('accounting', cost_center)

        return cost_center


    def sv_prompt(self, previous_result, error_description):
        prompt = (f"Der vorherige Versuch hat Fehler produziert: {error_description}. "
                  f"Bitte korrigiere diese Fehler nun. Das letzte Ergebnis war: {previous_result}.")
        improved_prompt = self.llm.invoke(prompt)
        print("Verbesserter Prompt generiert:", improved_prompt)
        return improved_prompt

    def ask_user(self, missing_info):
        user_input = input(f"Supervisor fragt: '{missing_info}'. Bitte geben Sie die fehlende Information ein: ")
        return user_input

    def save_intermediate_result(self, step, result):
        self.results[step] = result
        with open('data/intermediate_results.json', 'w') as file:
            json.dump(self.results, file, indent=4)
