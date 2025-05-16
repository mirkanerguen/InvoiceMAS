import streamlit as st
from agents.supervisor_agent import SupervisorAgent
from agents.approval_agent import ApprovalAgent
from config import RESULTS_PATH, ARCHIVE_DB_PATH
import tempfile
import pandas as pd
import re
import sqlite3
import json
from utils.login import check_credentials

st.title("Invoice-Workflow MAS")

if "workflow_done" not in st.session_state:
    st.session_state["workflow_done"] = False
if "sachlich_entscheidung" not in st.session_state:
    st.session_state["sachlich_entscheidung"] = None
if "login_erlaubt" not in st.session_state:
    st.session_state["login_erlaubt"] = False

uploaded_pdf = st.file_uploader("Rechnung hochladen (PDF)", type="pdf")

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    supervisor = SupervisorAgent(tmp_pdf_path)

    if st.button("Workflow starten"):
        with st.spinner("Workflow läuft..."):
            result = supervisor.action()
        st.session_state["workflow_done"] = True
        st.success("Workflow abgeschlossen!")

    if st.session_state["workflow_done"]:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            results = json.load(f)

        # Benutzerinteraktion (nach CheckAgent)
        if results.get("flag_wait_for_user_decision"):
            st.warning("Supervisor wartet auf Ihre Entscheidung.")

            if st.session_state["sachlich_entscheidung"] is None:
                st.markdown("**Sachliche Prüfung negativ. Trotzdem zur Genehmigung fortfahren?**")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Ja"):
                        st.session_state["sachlich_entscheidung"] = "ja"
                        st.session_state["login_erlaubt"] = True
                with col2:
                    if st.button("Nein"):
                        st.session_state["sachlich_entscheidung"] = "nein"
                        results["approval_status"] = "verweigert"
                        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
                            json.dump(results, f, indent=4)
                        st.error("Workflow abgebrochen durch Benutzerentscheidung.")
                        st.stop()

            if st.session_state["login_erlaubt"]:
                st.markdown("### Login zur Genehmigung")
                username = st.text_input("Benutzername")
                password = st.text_input("Passwort", type="password")

                rolle = results.get("expected_role", "teamlead")
                role_display = {
                    "employee": "Mitarbeiter",
                    "teamlead": "Teamleiter",
                    "departmentlead": "Abteilungsleiter",
                    "manager": "Manager"
                }.get(rolle, rolle)

                st.info(f"⚠️ Erwartete Rolle: **{role_display}**")

                if st.button("Login & fortsetzen"):
                    if check_credentials(username, password, rolle):
                        st.success("Login erfolgreich. Workflow wird fortgesetzt.")
                        results["flag_wait_for_user_decision"] = False
                        results["approval_status"] = "genehmigt"
                        results["approval"] = f"Genehmigt - Rolle: {role_display} (Login durch {username})"
                        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
                            json.dump(results, f, indent=4)
                        supervisor.continue_after_user_approval()
                    else:
                        st.error("Login fehlgeschlagen.")
                        st.stop()

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
        approval_status = results.get("approval_status", "")
        if approval_status == "verweigert":
            st.error("Freigabe wurde verweigert - Workflow beendet")
            st.stop()

        approval_text = results.get("approval", "")
        if isinstance(approval_text, str) and "Genehmigt" in approval_text:
            st.success(approval_text)
        elif isinstance(approval_text, str) and "Verweigert" in approval_text:
            st.error(approval_text)
        else:
            st.warning("Keine Freigabeentscheidung erfolgt.")

        # 5. Buchung
        st.markdown("### Ergebnis der Buchung:")
        booking_status = results.get("booking_status", "").lower()
        booking_text = results.get("booking", "")

        if "gebucht" in booking_status:
            st.success(booking_text)
        elif "abgebrochen" in booking_status:
            st.warning(booking_text)
        elif "offen" in booking_status:
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
