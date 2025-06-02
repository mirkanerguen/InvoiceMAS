# config.py – zentrale Konfigurationsdatei für Pfade, Rollen, Schwellenwerte und Modelle

# === Eigene Unternehmensdaten ===
OWN_COMPANY_NAME = "Karbo-Power UG"
OWN_COMPANY_ADDRESS = "Gutenbergstraße 32, 35043 Marburg"
OWN_COMPANY_FULL = f"{OWN_COMPANY_NAME}, {OWN_COMPANY_ADDRESS}"
# Wird im ValidationAgent verwendet, um Leistungsempfänger automatisch zu erkennen.

# === Archivverzeichnis für Ergebnisse und Originalrechnungen ===
ARCHIVE_DIR = "archive"

# === Wichtige Datenpfade (JSON, SQLite etc.) ===
RESULTS_PATH = "data/results.json"                         # Zwischenergebnisse der Agenten
ARCHIVE_DB_PATH = "data/archive.db"                        # SQLite-Datenbank zur Archivprüfung
INVOICE_FOLDER = "data/invoices/"                          # Optionaler Speicherort für PDF-Dateien
ARCHIVE_FOLDER = "archive/"                                # Zielordner für archivierte Rechnungen
REFERENCE_DATA_PATH = "data/known_transactions.json"       # Referenzdaten für CheckAgent
CREDENTIALS_PATH = "data/credentials.json"                 # Zugangsdaten für ApprovalAgent
WORKFLOW_STATUS_PATH = "data/workflow_status.json"         # Status-Tracking der Agenten (Streamlit)

# === Rollenzuweisungen für Genehmigungsschritte ===
TEAMLEITER_ROLE = "Teamleiter"
ABTEILUNGSLEITER_ROLE = "Abteilungsleiter"

# === Genutztes LLM-Modell über Ollama (lokal) ===
OLLAMA_MODEL = "mistral"

# === Schwellenwerte für Genehmigungsrollen (brutto) ===
APPROVAL_RULES = {
    "employee": 500,            # bis 500 EUR: Mitarbeiter
    "teamlead": 5000,           # bis 5.000 EUR: Teamleiter
    "departmentlead": 20000,    # bis 20.000 EUR: Abteilungsleiter
    "manager": float("inf")     # über 20.000 EUR: Manager
}

# === Debug-Modus aktivieren (für Entwicklungszwecke) ===
DEBUG_MODE = True
