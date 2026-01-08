import streamlit as st
import json
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# FIXED IMPORTS (No relative dots)
from agents import run_production_agent, run_integrity_agent, run_mother_agent
from memory import MemoryBank
from models import WorkoverCandidate

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="PetroAgent Orchestrator", 
    page_icon="🛢️", 
    layout="wide"
)

# Initialize Memory Bank
if 'brain' not in st.session_state:
    # Ensure this points to where you want the file saved relative to execution
    st.session_state.brain = MemoryBank(filename="data/workover_memory.json")

# Load Mock Data
def load_well_data():
    # If running from root folder, data is in "data/mock_db.json"
    file_path = "data/mock_db.json"
    
    # Fallback: if running inside app folder, try "../data/mock_db.json"
    if not os.path.exists(file_path):
        file_path = "../data/mock_db.json"

    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"❌ Data file not found! Checked path: {file_path}")
        return {}

# Initialize Data
if 'well_data' not in st.session_state:
    st.session_state.well_data = load_well_data()

well_data = st.session_state.well_data

# --- 2. UI HEADER ---
st.title("🛢️ PetroAgent: Workover Orchestrator")
st.markdown("""
**Autonomous Candidate Screening & Conflict Resolution System**
*Leveraging Multi-Agent AI to balance Production Potential vs. Well Integrity Constraints.*
""")

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("⚙️ Control Panel")
    
    if well_data:
        selected_well = st.selectbox("Select Target Well", list(well_data.keys()))
    else:
        selected_well = None
        st.warning("No well data loaded.")

    force_refresh = st.checkbox("Force Ignore Memory", value=False)
    
    st.divider()
    st.subheader("🧠 System Memory")
    stats = st.session_state.brain.get_stats()
    st.metric("Records", stats.get("total_records", 0))

# --- 4. MAIN WORKSPACE ---
if selected_well:
    col1, col2 = st.columns([1, 2])

    # --- LEFT COLUMN: DATA SNAPSHOT ---
    with col1:
        st.subheader("📊 Well Snapshot")
        data = well_data[selected_well]
        
        m1, m2 = st.columns(2)
        m1.metric("Current Oil", f"{data.get('last_test_oil', 0)} bopd")
        m2.metric("Potential", f"{data.get('potential_oil', 0)} bopd")
        
        st.caption("Technical Parameters:")
        st.dataframe(pd.DataFrame([data]).T, height=300, use_container_width=True)

    # --- RIGHT COLUMN: AGENT ORCHESTRATION ---
    with col2:
        st.subheader("🤖 Agent Operations")
        
        # --- A. TRIGGER BUTTON ---
        if st.button("🚀 Run Diagnosis", type="primary", use_container_width=True):
            
            cached_result = st.session_state.brain.recall(selected_well)
            
            if cached_result and not force_refresh:
                st.warning(f"⚡ CACHE HIT: Retrieved valid analysis from {cached_result.source}")
                st.session_state['current_result'] = cached_result
                
            else:
                with st.status("Orchestrating Multi-Agent System...", expanded=True) as status:
                    
                    st.write("👷 **Production Agent:** Analyzing decline curves...")
                    prod_report = run_production_agent(selected_well, data)
                    st.info(f"Prod Recommendation: {prod_report.recommendation}")
                    
                    st.write("🛡️ **Integrity Agent:** Checking wellbore diagrams...")
                    integ_report = run_integrity_agent(selected_well, data)
                    
                    if integ_report.blocking_flag:
                        st.error(f"Integrity Alert: {integ_report.issue_detected}")
                    else:
                        st.success("Integrity Check: Passed")
                    
                    st.write("👩‍💼 **Mother Agent:** Synthesizing final decision...")
                    final_decision = run_mother_agent(selected_well, prod_report, integ_report)
                    
                    st.session_state.brain.save_decision(selected_well, final_decision)
                    st.session_state['current_result'] = final_decision
                    status.update(label="Analysis Complete", state="complete", expanded=False)

        # --- B. RESULT DISPLAY & HUMAN OVERRIDE ---
        if 'current_result' in st.session_state:
            res = st.session_state['current_result']
            
            if res.well_id == selected_well:
                st.divider()
                
                if res.integrity_block:
                    st.error(f"⛔ DECISION: {res.proposed_job_type}")
                else:
                    st.success(f"✅ DECISION: {res.proposed_job_type}")
                
                st.markdown(f"**Technical Justification:**\n> {res.technical_justification}")
                
                row_info = st.columns(3)
                row_info[0].caption(f"📅 **Schedule:** {res.execution_date}")
                row_info[1].caption(f"🏷️ **Source:** {res.source}")
                
                # Supervisor Override
                with st.expander("📝 Supervisor Override / Approval", expanded=False):
                    with st.form("override_form"):
                        col_form_1, col_form_2 = st.columns(2)
                        with col_form_1:
                            new_job = st.text_input("Job Type", value=res.proposed_job_type)
                        with col_form_2:
                            try:
                                default_date = datetime.strptime(res.execution_date, "%Y-%m-%d")
                            except ValueError:
                                default_date = datetime.now() + timedelta(days=7)
                            new_date = st.date_input("Execution Date", value=default_date)
                        
                        new_reason = st.text_area("Notes", value="Approved by Senior Engineer.")
                        
                        if st.form_submit_button("✅ Approve & Update Memory"):
                            res.proposed_job_type = new_job
                            res.technical_justification = f"HUMAN OVERRIDE: {new_reason}"
                            res.execution_date = new_date.strftime("%Y-%m-%d")
                            res.source = "Human Supervisor"
                            res.integrity_block = False
                            
                            st.session_state.brain.save_decision(selected_well, res)
                            st.success("Memory updated! Reloading...")
                            time.sleep(1)
                            st.rerun()
            
            elif 'current_result' in st.session_state and res.well_id != selected_well:
                st.info("Click 'Run Diagnosis' to analyze this well.")