from agents.validation_agent import ValidationAgent
import json

class SupervisorAgent:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.validation_agent = ValidationAgent(pdf_path)

    def run_workflow(self):
        print("SupervisorAgent: Starte Validation-Agent.")
        validation_result = self.validation_agent.run()
        self.save_result(validation_result)
        return validation_result

    def save_result(self, result):
        with open("data/intermediate_results.json", "w") as f:
            json.dump({"validation": result}, f, indent=4)
