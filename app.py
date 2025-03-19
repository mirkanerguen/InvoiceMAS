import streamlit as st
from agents.supervisor_agent import SupervisorAgent
import tempfile

st.title("📄 InvoiceMAS Supervisor-Validation")

uploaded_pdf = st.file_uploader("Rechnung hochladen (PDF)", type="pdf")

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    supervisor = SupervisorAgent(tmp_pdf_path)

    if st.button("Validation-Agent starten"):
        with st.spinner("Validierung läuft..."):
            result = supervisor.run_workflow()
        st.success("Validierung abgeschlossen!")
        
        # Markdown-Tabelle ordentlich formatieren
        st.markdown("### 📑 Ergebnis der sachlichen Prüfung:")
        st.markdown(result.replace('|', '\|'), unsafe_allow_html=False)
        
        # Falls Markdown Tabelle Probleme macht, als Codeblock anzeigen:
        st.markdown("### 📑 Ergebnis (alternativ formatiert):")
        st.code(result, language="markdown")
