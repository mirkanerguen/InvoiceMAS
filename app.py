import streamlit as st
from agents.supervisor_agent import SupervisorAgent
import tempfile
import pandas as pd
import re

st.title("📄 InvoiceMAS Supervisor-Validation")

uploaded_pdf = st.file_uploader("Rechnung hochladen (PDF)", type="pdf")

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    supervisor = SupervisorAgent(tmp_pdf_path)

    if st.button("Validation-Agent starten"):
        with st.spinner("Validierung läuft..."):
            validation_result = supervisor.action()

            # Robuste DataFrame-Erstellung
            matches = re.findall(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', validation_result)
            header = [col.strip() for col in matches[0]]
            data_rows = [
                [col.strip() for col in row]
                for row in matches[1:]
                if '---' not in row[0] and row[0] != ''
            ]
            df_result = pd.DataFrame(data_rows, columns=header)

        st.success("Validierung abgeschlossen!")

        st.markdown("### 📑 Ergebnis der sachlichen Prüfung:")
        st.dataframe(df_result, use_container_width=True)
