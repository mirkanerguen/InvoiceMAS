import streamlit as st
import tempfile
import json
import re
import pandas as pd
import sqlite3
from config import RESULTS_PATH, ARCHIVE_DB_PATH
from agents.supervisor_agent import SupervisorAgent

st.set_page_config(page_title="Invoice Workflow MAS", layout="wide")
st.title("📄 Invoice-Workflow MAS")

# 1. Rechnung hochladen
uploaded_pdf = st.file_uploader("Rechnung hochladen (PDF)", type="pdf")

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    if st.button("🚀 Workflow starten"):
        with st.spinner("Agenten werden ausgeführt..."):
            supervisor = SupervisorAgent(tmp_pdf_path)
            result = supervisor.action()
        st.success("Workflow abgeschlossen!")

# 2. Ergebnisse laden (wenn vorhanden)
try:
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)
except FileNotFoundError:
    st.stop()

# 3. Entscheidung bei negativer sachlicher Prüfung
if results.get("flag_wait_for_user_decision"):
    st.warning("Sachliche Prüfung war negativ. Soll der Workflow trotzdem fortgesetzt werden?")
    col1, col2 = st.columns(2)
    if col1.button("Ja – trotzdem fortsetzen"):
        supervisor = SupervisorAgent("")  # pdf_path leer, da nicht mehr benötigt
        with st.spinner("Genehmigung, Buchung & Archivierung werden fortgesetzt..."):
            supervisor.continue_after_user_approval()
        st.success("Fortsetzung abgeschlossen.")
        st.rerun()
    if col2.button("Nein – Workflow abbrechen"):
        results["approval_status"] = "verweigert"
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        st.error("Workflow manuell abgebrochen.")
        st.stop()

# 4. Ergebnisse anzeigen (wenn kein Warten mehr)
st.subheader("1️⃣ Formelle Prüfung (§14 UStG)")
validation_result = results.get("validation", "")
matches = re.findall(r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", validation_result)
if matches:
    df = pd.DataFrame(matches[1:], columns=matches[0])
    st.dataframe(df, use_container_width=True)
else:
    st.info("Keine gültige Tabelle aus der formellen Prüfung extrahierbar.")

st.subheader("2️⃣ Kostenstelle")
st.success(results.get("accounting", "Keine Zuordnung erfolgt."))

st.subheader("3️⃣ Sachliche Prüfung")
check = results.get("check", "")
if check == "sachlich_korrekt":
    st.success("Sachlich korrekt – plausible Übereinstimmung mit bekannten Transaktionen.")
elif check == "nicht_nachvollziehbar":
    st.error("Nicht nachvollziehbar – keine passende Vergleichstransaktion.")
elif check == "unklar":
    st.warning("Unklare KI-Antwort – manuelle Prüfung empfohlen.")
else:
    st.info("Kein Prüfergebnis vorhanden.")

st.subheader("4️⃣ Freigabeentscheidung")
approval = results.get("approval", "")
if "Genehmigt" in approval:
    st.success(approval)
elif "Verweigert" in approval:
    st.error(approval)
else:
    st.warning("Keine Genehmigung erteilt.")

st.subheader("5️⃣ Buchung")
booking = results.get("booking", "")
status = results.get("booking_status", "")
if status == "gebucht":
    st.success(booking)
elif status == "abgebrochen":
    st.warning(booking)
else:
    st.info("Keine Buchung erfolgt.")

st.subheader("6️⃣ Archivierung")
archive_info = results.get("archive", "")
if archive_info and "Archiviert unter" in archive_info:
    st.success(archive_info)
else:
    st.info("Keine Archivierungsinformationen gefunden.")

st.subheader("📚 Archivierte Rechnungen")
try:
    conn = sqlite3.connect(ARCHIVE_DB_PATH)
    df_archiv = pd.read_sql_query("SELECT * FROM archive", conn)
    conn.close()
    st.dataframe(df_archiv, use_container_width=True)
except Exception:
    st.info("Noch keine archivierten Rechnungen vorhanden.")
