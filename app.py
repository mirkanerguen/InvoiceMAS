import streamlit as st
from agents.supervisor_agent import SupervisorAgent
import tempfile
import pandas as pd
import re
import sqlite3
import json

st.title("Invoice-Workflow MAS")

uploaded_pdf = st.file_uploader("Rechnung hochladen (PDF)", type="pdf")

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    supervisor = SupervisorAgent(tmp_pdf_path)

    if st.button("Workflow starten"):
        with st.spinner("Workflow läuft..."):
            result = supervisor.action()

        st.success("Workflow abgeschlossen!")

        with open("data/results.json", "r") as f:
            results = json.load(f)

        # 1. Formelle Prüfung
        validation_result = results.get("validation", "")
        st.markdown("### Ergebnis der formellen Prüfung:")
        if "|" in validation_result:
            matches = re.findall(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', validation_result)
            if matches:
                header = [col.strip() for col in matches[0]]
                data_rows = [
                    [col.strip() for col in row]
                    for row in matches[1:]
                    if "---" not in row[0] and row[0] != ""
                ]
                df_validation = pd.DataFrame(data_rows, columns=header)
                st.dataframe(df_validation, use_container_width=True)

        # 2. Kostenstelle
        st.markdown("### Ergebnis der Kostenstellen-Zuordnung:")
        cost_center = results.get("accounting", "Nicht zugewiesen")
        st.success(f"Zugeordnete Kostenstelle: **{cost_center}**")

        # 3. Ergebnis der sachlichen Prüfung
        check_result = results.get("check", "")
        st.markdown("###   Ergebnis der sachlichen Prüfung:")
        if check_result == "sachlich_korrekt":
            st.success("Sachlich korrekt – plausibler Abgleich mit bekannten Transaktionen.")
        elif check_result == "nicht_nachvollziehbar":
            st.error("Sachlich nicht nachvollziehbar – kein Abgleich mit interner Referenz möglich.")
        elif check_result == "unklar":
            st.warning("Unklare KI-Antwort – manuelle Prüfung empfohlen.")
        else:
            st.info("Kein Ergebnis zur sachlichen Prüfung vorhanden.")


        # 4. Freigabe
        st.markdown("### Ergebnis der finalen Freigabe:")
        approval_text = results.get("approval", "")
        approval_status = results.get("approval_status", "")
        if "Genehmigt" in approval_text:
            st.success(approval_text)
        elif "Verweigert" in approval_text:
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
        conn = sqlite3.connect("data/archive.db")  
        df_archive = pd.read_sql_query("SELECT * FROM archive", conn)
        conn.close()
        st.dataframe(df_archive, use_container_width=True)
