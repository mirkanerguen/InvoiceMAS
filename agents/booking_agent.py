import json
import re
import sqlite3
from langchain_community.llms import Ollama
from config import RESULTS_PATH, ARCHIVE_DB_PATH, OLLAMA_MODEL

class BookingAgent:
    def __init__(self, intermediate_path=RESULTS_PATH):
        # Initialisierung des LLM und Laden des result.json
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.path = intermediate_path

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def goal(self):
        # Zieldefinition: Buchung durchführen und als "gebucht" markieren
        return "Führe die Buchung der freigegebenen Rechnung durch und kennzeichne sie als gebucht."

    def think(self):
        # Wenn die Rechnung schon gebucht wurde, abbrechen
        if self.data.get("booking_status") == "gebucht":
            return "Diese Rechnung wurde bereits gebucht. Keine Aktion notwendig."
        return "Die Rechnung ist freigegeben und kann jetzt gebucht werden."

    def is_invoice_already_booked(self, rechnungsnummer: str) -> bool:
        # Prüfe anhand der Archivdatenbank, ob die Rechnung schon archiviert (also gebucht) wurde
        conn = sqlite3.connect(ARCHIVE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE rechnungsnummer = ?", (rechnungsnummer,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def extract_amount_with_llm(self, validation_text: str) -> str:
        # 1. Versuch: LLM soll den Bruttobetrag aus Zeile 9 extrahieren
        prompt = f"""
    Du bist ein Buchhaltungsassistent. Extrahiere aus folgendem Text den **Brutto- oder Gesamtbetrag der Rechnung** in Euro.

    Der Text stammt aus Zeile 9 der extrahierten Rechnungstabelle gemäß §14 UStG (Entgelt nach Steuersätzen aufgeschlüsselt).  
    Beispiel: "2.450,00 € (Netto), 465,50 € (Steuer), 2.915,50 € (Brutto)"

    Deine Aufgabe:
    - Ignoriere alle Netto- oder Steuerbeträge.
    - Wähle die höchste Zahl im Kontext von "Brutto" oder "Gesamt".
    - Gib **nur den Betrag**, **ohne Währungszeichen oder Text**, **mit Punkt** als Dezimaltrenner zurück, z. B.: 2915.50

    Hier der Text:
    {validation_text}

    Antwort:
    """
        response = self.llm.invoke(prompt).strip()

        # Versuche, den extrahierten Betrag zu parsen
        match = re.search(r"([\d]+[\.,]?[\d]*)", response)
        if match:
            betrag = match.group(1).replace(",", ".")
            try:
                betrag_float = float(betrag)
                if betrag_float >= 100:  # Filter gegen zu kleine Werte oder fehlerhafte Antworten
                    return f"{betrag_float:.2f}"
            except ValueError:
                pass

        # 2. Fallback: Größte Zahl aus dem gesamten Validierungstext verwenden
        print("LLM konnte Betrag nicht zuverlässig extrahieren - Fallback aktiv.")
        zahlen = re.findall(r"[\d]+[\.,][\d]+", validation_text.replace(",", "."))
        zahlen_float = [float(z) for z in zahlen]

        if zahlen_float:
            max_betrag = max(zahlen_float)
            return f"{max_betrag:.2f}"

        # Wenn alles fehlschlägt, Standardwert zurückgeben
        return "0.00"

    def action(self):
        # Denkprozess ausführen
        gedanke = self.think()
        validation = self.data.get("validation", "")

        # Extrahiere die Rechnungsnummer aus Zeile 6
        match_nr = re.search(r"\|6\. Fortlaufende Rechnungsnummer\s*\|\s*Ja\s*\|\s*(.*?)\s*\|", validation)
        rechnungsnummer = match_nr.group(1).strip() if match_nr else "UNBEKANNT"

        # Abbruch, wenn bereits gebucht (doppelte Buchung vermeiden)
        if self.is_invoice_already_booked(rechnungsnummer):
            result = f"Buchung abgebrochen - Rechnung {rechnungsnummer} wurde bereits gebucht."
            self.data["booking"] = result
            self.data["booking_status"] = "abgebrochen"
            self._save()
            return result

        # Hole die Kostenstelle und den Bruttobetrag
        kostenstelle = self.data.get("accounting", "Unbekannt")
        betrag = self.extract_amount_with_llm(validation)

        # LLM soll simulierte Buchungsbestätigung erzeugen
        buchung_prompt = f"""
Du bist ein Buchhaltungs-Agent. Dein Ziel: Simuliere die Buchung der Rechnung.

Rechnungsdaten:
- Kostenstelle: {kostenstelle}
- Betrag brutto: {betrag} EUR

Gib folgenden Satz exakt aus:
Buchung erfolgt: [Betrag] EUR auf [Kostenstelle] - Status: gebucht
"""
        buchung_text = self.llm.invoke(buchung_prompt).strip()

        # Ergebnisse in result.json speichern
        self.data["booking"] = buchung_text
        self.data["booking_status"] = "gebucht"
        self._save()

        return buchung_text

    def _save(self):
        # Speichere Änderungen in results.json
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
