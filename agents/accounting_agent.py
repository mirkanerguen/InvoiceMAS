from langchain_community.llms import Ollama
import json
from utils.kostenstellen import KOSTENSTELLEN_REGELN, DEFAULT_KOSTENSTELLE

class AccountingAgent:
    def __init__(self, validation_result_path):
        self.llm = Ollama(model="mistral")
        with open(validation_result_path, "r") as file:
            self.data = json.load(file)["validation"]

    def goal(self):
        return "Weise die Rechnung anhand ihrer Positionen einer passenden Kostenstelle zu."

    def think(self):
        return "Untersuche die Leistung(en) in der Rechnung und finde die passende Kostenstelle."

    def action(self):
        prompt = f"""
Du bist ein Buchhaltungs-Agent. Dein Ziel ist es, den Rechnungsinhalt einer passenden Kostenstelle zuzuordnen. 
Du erhältst die extrahierten Pflichtangaben einer Rechnung im Tabellenformat.

Dein Vorgehen:
1. Lies den Inhalt der Spalte 'Extrahierter Wert' zur Leistung (Zeile 7).
2. Ordne diese anhand folgender Zuordnungstabelle einer fiktiven Kostenstelle zu:

Beratung, Businessplan, Gespräche → 1001-Beratung  
Software, Lizenz → 1002-IT  
Marketing, Werbung → 1003-Marketing  
Hardware → 1004-Beschaffung  
Schulung → 1005-Personal  
Sonstiges → 1099-Sonstiges  

Rechnungsauszug:
{self.data}

Antwortformat: Nur Kostenstelle (z. B. „1001-Beratung“)
"""

        kostenstelle = self.llm.invoke(prompt).strip()
        return kostenstelle
