import json
import re
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from config import OLLAMA_MODEL, RESULTS_PATH
from utils.cost_center import COST_CENTER_RULES, DEFAULT_COST_CENTER

class AccountingAgent:
    def __init__(self, validation_result_path=RESULTS_PATH):
        # Initialisiere das LLM (lokales Mistral-Modell über Ollama)
        self.llm = Ollama(model=OLLAMA_MODEL)
        # Lade das Ergebnis der Validierung (Pflichtangaben-Tabelle) aus der JSON-Datei
        with open(validation_result_path, "r", encoding="utf-8") as file:
            self.data = json.load(file).get("validation", "")

    def goal(self):
        # Ziel des Agents in einem Satz – wird u.a. im Prompt verwendet
        return "Weise die Rechnung anhand ihrer Positionen einer passenden Kostenstelle zu."

    def think(self):
        # Extrahiere aus der Validierung die Leistung (Pflichtangabe 7)
        # Die Leistung wird benötigt, um daraus semantisch eine Kostenstelle zu erschließen
        match = re.findall(r"7\.\s*Menge.*?\|\s*Ja\s*\|\s*(.*?)\|", self.data.replace("\n", " "))
        leistung_text = match[0].strip() if match else "nicht gefunden"

        # Prompt für ein erstes „Nachdenken“ des Agents zur Interpretation der Leistung
        thought_prompt = PromptTemplate(
            input_variables=["goal", "leistung"],
            template="""Du bist ein intelligent handelnder Agent in der Buchhaltung.
Dein Ziel lautet: {goal}

Analysiere den folgenden Rechnungsinhalt aus der Spalte „Leistung“:
"{leistung}"

Überlege, wie diese Leistung sinnvoll in eine Kostenstelle eingeordnet werden kann. Antworte mit einem Satz.
"""
        )

        # LLM-Antwort auf das Think-Prompt abrufen
        thought = self.llm.invoke(thought_prompt.format(
            goal=self.goal(),
            leistung=leistung_text
        ))

        print(f"AccountingAgent Think(): {thought.strip()}")
        return thought.strip()

    def action(self, agent_thoughts=None):
        # Falls kein Gedanke übergeben wurde, wird dieser aus think() erzeugt
        if not agent_thoughts:
            agent_thoughts = self.think()

        # Baue den Regel-Text auf, mit dem das LLM die richtige Kostenstelle zuordnen soll
        regel_text = "\n".join([f"{k.capitalize()} → {v}" for k, v in COST_CENTER_RULES.items()])

        # Haupt-Prompt für die Zuweisung einer Kostenstelle
        prompt = f"""
Du bist ein Buchhaltungs-Agent. Ziel: Weise die folgende Leistung einer passenden fiktiven Kostenstelle zu.

Aktueller Gedanke: {agent_thoughts}

Verwende folgende Regeln:
{regel_text}
Sonstiges → {DEFAULT_COST_CENTER}

Rechnungsauszug (Pflichtangaben-Tabelle):
{self.data}

Antwortformat: Nur Kostenstelle, z. B.: 1001-Beratung
"""

        # LLM-Antwort enthält die finale Kostenstellen-Zuweisung
        costcenter = self.llm.invoke(prompt).strip()
        print(f"AccountingAgent Action(): {costcenter}")
        return costcenter
