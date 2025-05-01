from langchain_community.llms import Ollama
import json
from utils.cost_center import COST_CENTER_RULES, DEFAULT_COST_CENTER
from langchain.prompts import PromptTemplate

class AccountingAgent:
    def __init__(self, validation_result_path):
        self.llm = Ollama(model="mistral")
        with open(validation_result_path, "r") as file:
            self.data = json.load(file)["validation"]

    def goal(self):
        return "Weise die Rechnung anhand ihrer Positionen einer passenden Kostenstelle zu."

    def think(self):
        # Extrahiere den Leistungsblock aus der Tabelle (Zeile 7 = "7. Menge und Art der gelieferten Leistung")
        import re
        match = re.findall(r"7\.\s*Menge.*?\|\s*Ja\s*\|\s*(.*?)\|", self.data.replace("\n", " "))
        leistung_text = match[0].strip() if match else "nicht gefunden"

        thought_prompt = PromptTemplate(
            input_variables=["goal", "leistung"],
            template="""Du bist ein intelligent handelnder Agent in der Buchhaltung.
Dein Ziel lautet: {goal}

Analysiere den folgenden Rechnungsinhalt aus der Spalte „Leistung“:
"{leistung}"

Überlege, wie diese Leistung sinnvoll in eine Kostenstelle eingeordnet werden kann. Antworte mit einem Satz.
"""
        )

        thought = self.llm.invoke(thought_prompt.format(
            goal=self.goal(),
            leistung=leistung_text
        ))

        print(f"AccountingAgent Think(): {thought}")
        return thought.strip()

    def action(self, agent_thoughts=None):
        if not agent_thoughts:
            agent_thoughts = self.think()

        prompt = f"""
Du bist ein Buchhaltungs-Agent. Ziel: Weisen Sie die folgende Leistung einer passenden fiktiven Kostenstelle zu.

Aktueller Gedanke: {agent_thoughts}

Verwende folgende Regeln:

Beratung, Businessplan, Gespräche → 1001-Beratung  
Software, Lizenz → 1002-IT  
Marketing, Werbung → 1003-Marketing  
Hardware → 1004-Beschaffung  
Schulung → 1005-Personal  
Sonstiges → 1099-Sonstiges  

Rechnungsauszug (Pflichtangaben-Tabelle):
{self.data}

Antwortformat: Nur Kostenstelle, z. B.: 1001-Beratung
"""

        costcenter = self.llm.invoke(prompt).strip()
        print(f"AccountingAgent Action(): {costcenter}")
        return costcenter
