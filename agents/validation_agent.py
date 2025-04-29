from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from utils.pdf_parser import extract_text_from_pdf
   
import pandas as pd
import re
class ValidationAgent:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.invoice_text = extract_text_from_pdf(pdf_path)
        self.llm = Ollama(model="mistral")

    def goal(self):
        return "Alle Pflichtangaben gemäß §14 UStG müssen vorhanden und korrekt extrahiert sein."

    def prompt(self):
        return PromptTemplate(
            input_variables=["invoice_text", "agent_thoughts"],
            template="""Du bist ein KI-Agent zur präzisen Prüfung und Extraktion der sachlichen Richtigkeit einer Rechnung gemäß §14 UStG.

    Deine aktuellen Gedanken sind: {agent_thoughts}

    Extrahiere aus dem Rechnungstext folgende Pflichtangaben exakt und ohne Zusatzinformationen.
    Falls Angaben nicht vorhanden sind, gib exakt „Fehlt“ an.

    Achte ganz genau darauf, wer der leistende Unternehmer und wer der Leistungsempfänger ist, und ordne die Namen und Anschriften exakt korrekt zu!

    Generiere exakt diese Tabelle im Markdown-Format (Jede Tabellenzeile unbedingt mit Zeilenumbruch, KEINE Zeilenumbrüche innerhalb einer Zeile!):

    | Pflichtangabe | Vorhanden | Extrahierter Wert |
    |---------------|-----------|-------------------|
    | 1. Name & Anschrift des leistenden Unternehmers | Ja/Nein | Nur Name und Anschrift |
    | 2. Name & Anschrift des Leistungsempfängers | Ja/Nein | Nur Name und Anschrift |
    | 3. Steuernummer des Unternehmers | Ja/Nein | Nur die Steuernummer |
    | 4. Umsatzsteuer-ID des Unternehmers | Ja/Nein | Nur die Umsatzsteuer-ID |
    | 5. Ausstellungsdatum | Ja/Nein | Datum |
    | 6. Fortlaufende Rechnungsnummer | Ja/Nein | Rechnungsnummer |
    | 7. Menge und Art der gelieferten Leistung | Ja/Nein | Aufzählung der Leistungen (kurz) |
    | 8. Zeitpunkt der Leistung oder Leistungszeitraum | Ja/Nein | Zeitraum oder Datum |
    | 9. Entgelt nach Steuersätzen aufgeschlüsselt | Ja/Nein | Netto-, Bruttobetrag, Steuerbetrag |
    | 10. Steuersatz oder Hinweis auf Steuerbefreiung | Ja/Nein | Steuersatz oder Hinweis |
    | 11. Hinweis auf Aufbewahrungspflicht (§14b UStG) | Ja/Nein | Exakt "Hinweis vorhanden" oder "Fehlt" |
    | 12. Angabe „Gutschrift“ (falls zutreffend) | Ja/Nein | Exakt "Gutschrift" oder "Fehlt" |

    Rechnungstext:
    {invoice_text}
    """
        )

    def think(self):
        thought_prompt = PromptTemplate(
            input_variables=["invoice_text", "goal"],
            template="""Du bist ein intelligenter KI-Agent, der eine Rechnung prüft.

            Dein Ziel lautet: {goal}

            Analysiere kurz den Rechnungstext und beschreibe in einem Satz, was dein nächster Schritt ist, um das Ziel zu erreichen.

            Rechnungstext: {invoice_text}

            Antworte kurz und präzise mit einem Satz."""
        )

        formatted_thought_prompt = thought_prompt.format(
            invoice_text=self.invoice_text,
            goal=self.goal()
        )

        agent_thoughts = self.llm.invoke(formatted_thought_prompt)
        print(f"ValidationAgent Think(): {agent_thoughts}")
        return agent_thoughts.strip()

    def action(self, agent_thoughts, custom_prompt=None):
        if custom_prompt:
            formatted_prompt = custom_prompt
        else:
            formatted_prompt = self.prompt().format(
                invoice_text=self.invoice_text,
                agent_thoughts=agent_thoughts
            )
        result = self.llm.invoke(formatted_prompt)

        # Robuste Methode: Jede Zeile explizit trennen (jede Tabellenzeile auf eine eigene Zeile)
        result = result.replace("\n", " ")
        result = re.sub(r"\|\s*(\d+\.)", r"\n|\1", result)

        clean_result = result.strip()
        print("ValidationAgent Action(): Daten extrahiert.")
        return clean_result




    # Standardmethode ohne Anpassung
    def run(self):
        thoughts = self.think()
        action_result = self.action(thoughts)
        return action_result

    # Methode mit vom Supervisor verbesserten Prompt
    def run_with_prompt(self, improved_prompt):
        thoughts = self.think()
        action_result = self.action(thoughts, custom_prompt=improved_prompt)
        return action_result

    # Methode zur manuellen User-Eingabe
    def run_with_user_input(self, missing_info):
        user_input_prompt = self.prompt().format(
            invoice_text=f"{self.invoice_text}\n\nVom User ergänzte Information: {missing_info}",
            agent_thoughts="Der User hat die fehlende Information ergänzt."
        )
        action_result = self.action("User-ergänzte Eingabe", custom_prompt=user_input_prompt)
        return action_result
 


    def to_dataframe(self, markdown_table):
        # Nutze Regex zur Extraktion jeder Tabellenzeile zuverlässig
        pattern = r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
        matches = re.findall(pattern, markdown_table)

        if not matches or len(matches) < 2:
            raise ValueError(f"Ungültige Tabelle erhalten:\n{markdown_table}")

        header = [col.strip() for col in matches[0]]

        data_rows = [
            [col.strip() for col in row] for row in matches[1:]
            if "---" not in row[0] and row[0] != ""
        ]

        df = pd.DataFrame(data_rows, columns=header)
        return df
