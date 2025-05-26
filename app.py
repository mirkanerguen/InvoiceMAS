import streamlit as st
from agents.supervisor_agent import SupervisorAgent
from config import WORKFLOW_STATUS_PATH
import tempfile
import json
import os
import time

st.set_page_config(layout="wide")
st.title("💼 Agentischer Workflow zur Rechnungsfreigabe")

uploaded_pdf = st.file_uploader("Bitte Rechnung hochladen (PDF)", type="pdf")


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
    emoji = {0: "🔴", 1: "🟡", 2: "🟢", 3: "🔵"}

    with container:
        bar = " → ".join(
            f"{emoji[status[k]]} {labels[k]}" for k in labels
        )
        st.markdown(f"### 📊 Workflow-Fortschritt\n{bar}")

    # Rückgabe: True, wenn alles auf grün
    return all(v == 2 for v in status.values())


# === Hauptprozess: Supervisor + Live-Update ===
if uploaded_pdf:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.getbuffer())
        tmp_pdf_path = tmp_file.name

    initialize_workflow_status()
    supervisor = SupervisorAgent(tmp_pdf_path)

    status_container = st.empty()  # Live-Fortschritt
    render_status_bar(status_container)
    if st.button("Workflow starten"):
        st.info("Supervisor startet den Workflow. Fortschritt unten sichtbar:")

        workflow_done = False
        while not workflow_done:
            result = supervisor.action()
            workflow_done = render_status_bar(status_container)
            time.sleep(1.2)  # UI-Update sichtbar machen

        st.success("✅ Workflow erfolgreich abgeschlossen!")

        # Ergebnis-Anzeige aus results.json
        st.markdown("### 🧾 Ergebnisse aus results.json")
        with open("data/results.json", "r", encoding="utf-8") as f:
            results = json.load(f)
        st.json(results, expanded=True)

