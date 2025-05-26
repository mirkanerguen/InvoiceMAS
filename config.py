# config.py

OWN_COMPANY_NAME = "Karbo-Power UG"
OWN_COMPANY_ADDRESS = "Gutenbergstraße 32, 35043 Marburg"
OWN_COMPANY_FULL = f"{OWN_COMPANY_NAME}, {OWN_COMPANY_ADDRESS}"

# Archivpfade
ARCHIVE_DIR = "archive"

# Datenpfade
RESULTS_PATH = "data/results.json"
ARCHIVE_DB_PATH = "data/archive.db"
INVOICE_FOLDER = "data/invoices/"
ARCHIVE_FOLDER = "archive/"
REFERENCE_DATA_PATH = "data/known_transactions.json"
CREDENTIALS_PATH = "data/credentials.json"
WORKFLOW_STATUS_PATH = "data/workflow_status.json"

# Login-Logik
TEAMLEITER_ROLE = "Teamleiter"
ABTEILUNGSLEITER_ROLE = "Abteilungsleiter"

# LLM-Modelle
OLLAMA_MODEL = "mistral"


# Genehmigungsgrenzen
APPROVAL_RULES = {
    "employee": 500,
    "teamlead": 5000,
    "departmentlead": 20000,
    "manager": float("inf")
}


# Debug
DEBUG_MODE = True
