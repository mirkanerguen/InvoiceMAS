import streamlit as st
from agents.supervisor_agent import SupervisorAgent
import tempfile
import pandas as pd
import re

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

        # Zwischenergebnisse laden
        import json
        with open("data/intermediate_results.json", "r") as f:
            results = json.load(f)

        # 1. Ergebnis der formellen Prüfung
        validation_result = results.get("validation", "")
        st.markdown("###   Ergebnis der formellen Prüfung:")
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

        #  2. Ergebnis der Kostenstellen-Zuordnung
        cost_center = results.get("accounting", "")
        st.markdown("###   Ergebnis der Accounting-Zuordnung:")
        st.success(f"Zugeordnete Kostenstelle: **{cost_center}**")
        
        # 3. Ergebnis der sachlichen Prüfung
        check_result = results.get("check", "")
        st.markdown("###   Ergebnis der sachlichen Prüfung:")
        if check_result.startswith("✅"):
            st.success(check_result)
        else:
            st.error(check_result)
