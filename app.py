import streamlit as st
from agents.supervisor_agent import SupervisorAgent
from config import RESULTS_PATH, ARCHIVE_DB_PATH
import tempfile
import pandas as pd
import re
import sqlite3
import json

st.title("Invoice-Workflow MAS")

uploaded_pdf = st.file_uploader("Rechnung hochladen (PDF)", type="pdf")


def markdown_table_to_df(markdown):
    pattern = r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    matches = re.findall(pattern, markdown.strip())
    if not matches or len(matches) < 2:
        raise ValueError("Markdown-Tabelle nicht erkannt.")

    headers = list(matches[0])
    rows = matches[1:]
    return pd.DataFrame(rows, columns=headers)

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    supervisor = SupervisorAgent(tmp_pdf_path)

    if st.button("Workflow starten"):
        with st.spinner("Workflow läuft..."):
            result = supervisor.action()

        st.success("Workflow abgeschlossen!")

        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            results = json.load(f)

        # 1. Formelle Prüfung
        validation_result = results.get("validation", "")
        st.markdown("### Ergebnis der formellen Prüfung:")
        try:
            df_validation = markdown_table_to_df(validation_result)
            st.dataframe(df_validation, use_container_width=True)
        except Exception as e:
            st.warning(f"Tabelle konnte nicht dargestellt werden: {e}")

        # 2. Kostenstelle
        st.markdown("### Ergebnis der Kostenstellen-Zuordnung:")
        cost_center = results.get("accounting", "Nicht zugewiesen")
        st.success(f"Zugeordnete Kostenstelle: **{cost_center}**")

        # 3. Sachliche Prüfung
        st.markdown("### Ergebnis der sachlichen Prüfung:")
        check_result = results.get("check", "")
        if check_result == "sachlich_korrekt":
            st.success("Sachlich korrekt - plausibler Abgleich mit bekannten Transaktionen.")
        elif check_result == "nicht_nachvollziehbar":
            st.error("Sachlich nicht nachvollziehbar - kein Abgleich mit interner Referenz möglich.")
        elif check_result == "unklar":
            st.warning("Unklare KI-Antwort - manuelle Prüfung empfohlen.")
        else:
            st.info("Kein Ergebnis zur sachlichen Prüfung vorhanden.")

        # 4. Freigabe
        st.markdown("### Ergebnis der finalen Freigabe:")
        approval_text = results.get("approval", "")
        if isinstance(approval_text, str) and "Genehmigt" in approval_text:
            st.success(approval_text)
        elif isinstance(approval_text, str) and "Verweigert" in approval_text:
            st.error(approval_text)
        else:
            st.warning("Keine Freigabeentscheidung erfolgt.")

        # 5. Buchung
        st.markdown("### Ergebnis der Buchung:")
        booking_text = results.get("booking", "")
        if "gebucht" in booking_text.lower():
            st.success(booking_text)
        elif "abgebrochen" in booking_text.lower():
            st.warning(booking_text)
        elif "offen" in booking_text.lower():
            st.info("Noch keine Buchung erfolgt.")
        else:
            st.error("Unbekannter Buchungsstatus.")

        # 6. Archivierung
        st.markdown("### Archivierung:")
        archive_info = results.get("archive", "Keine Archivierungsinformationen.")
        st.info(archive_info)

        # 7. Historie (Archivierte Rechnungen)
        st.markdown("### Archivierte Rechnungen:")
        conn = sqlite3.connect(ARCHIVE_DB_PATH)
        df_archive = pd.read_sql_query("SELECT * FROM archive", conn)
        conn.close()
        st.dataframe(df_archive, use_container_width=True)





