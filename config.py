# config.py

# Archivpfade
ARCHIVE_DIR = "archive"

# Datenpfade
RESULTS_PATH = "data/results.json"
ARCHIVE_DB_PATH = "data/archive.db"
INVOICE_FOLDER = "data/invoices/"
ARCHIVE_FOLDER = "archive/"
REFERENCE_DATA_PATH = "data/known_transactions.json"
CREDENTIALS_PATH = "data/credentials.json"

# Login-Logik
TEAMLEITER_ROLE = "Teamleiter"
ABTEILUNGSLEITER_ROLE = "Abteilungsleiter"

# LLM-Modelle
OLLAMA_MODEL = "mistral"


# Genehmigungsgrenzen
APPROVAL_THRESHOLDS = {
    1: 500.00,    # bis 500 → Mitarbeiter
    2: 5000.00,   # bis 5000 → Teamleiter
    3: float("inf")  # darüber → Abteilungsleiter
}

# Debug
DEBUG_MODE = True
