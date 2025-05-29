# app.py
import streamlit as st
from agents.supervisor_agent import SupervisorAgent
from config import WORKFLOW_STATUS_PATH
import tempfile
import json
import os
import time

st.set_page_config(layout="wide")
st.title("💼 Agentischer Workflow zur Rechnungsfreigabe")

# === Initialstatus setzen ===
def initialize_workflow_status():
    default_status = {
        "1_validation": 0,
        "2_accounting": 0,
        "3_check": 0,
        "4_approval": 0,
        "5_booking": 0,
        "6_archiving": 0
    }
    os.makedirs(os.path.dirname(WORKFLOW_STATUS_PATH), exist_ok=True)
    with open(WORKFLOW_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(default_status, f, indent=4)

# === Fortschrittsleiste visualisieren ===
def render_status_bar(container):
    with open(WORKFLOW_STATUS_PATH, "r", encoding="utf-8") as f:
        status = json.load(f)

    labels = {
        "1_validation": "Validation",
        "2_accounting": "Accounting",
        "3_check": "Check",
        "4_approval": "Approval",
        "5_booking": "Booking",
        "6_archiving": "Archiving"
    }
    emoji = {0: "⚪", 1: "🟡", 2: "🟢", 3: "🔴"}

    with container:
        bar = " → ".join(f"{emoji[status[k]]} {labels[k]}" for k in labels)
        st.markdown(f"### 📊 Workflow-Fortschritt\n{bar}")

    return all(v == 2 for v in status.values())

# === SessionState vorbereiten ===
if "supervisor" not in st.session_state:
    st.session_state.supervisor = None
if "workflow_done" not in st.session_state:
    st.session_state.workflow_done = False

# === Datei-Upload ===
uploaded_pdf = st.file_uploader("Bitte Rechnung hochladen (PDF)", type="pdf")

if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    if st.session_state.supervisor is None:
        initialize_workflow_status()
        st.session_state.supervisor = SupervisorAgent(tmp_pdf_path)

    status_container = st.empty()
    render_status_bar(status_container)

    if not st.session_state.workflow_done:
        st.info("⚙️ Workflow wird automatisch gestartet...")
        while True:
            step_result = st.session_state.supervisor.next_step()
            render_status_bar(status_container)
            time.sleep(1.5)

            if step_result == "Done":
                st.session_state.workflow_done = True
                st.success("✅ Workflow erfolgreich abgeschlossen!")
                break
            elif "Abbruch" in step_result:
                st.session_state.workflow_done = True
                st.error(f"⛔ {step_result}")
                break
            else:
                st.info(f"ℹ️ {step_result}")

    else:
        st.success("✅ Workflow vollständig abgeschlossen.")

    # === Ergebnisse anzeigen ===
    if st.session_state.workflow_done:
        st.markdown("### 🧾 Ergebnisse aus results.json")
        with open("data/results.json", "r", encoding="utf-8") as f:
            results = json.load(f)
        st.json(results, expanded=True)
