import os
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# FIXED IMPORT (No relative dot)
from models import AgentDiagnosis, WorkoverCandidate, ExecutionPlan

# Load environment variables (API Key)
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- CORE AGENT ENGINE ---
def run_llm_agent(agent_name: str, system_prompt: str, user_data: str, response_model: BaseModel):
    """
    Generic wrapper to call OpenAI with Structured Outputs.
    """
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06", 
            messages=[
                {"role": "system", "content": f"You are the {agent_name}. {system_prompt}"},
                {"role": "user", "content": f"Here is the data context: {user_data}"},
            ],
            response_format=response_model,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"Error running {agent_name}: {e}")
        # In production, you might return a default "Error" object here
        return None

# --- 1. PRODUCTION AGENT ---
def run_production_agent(well_id: str, well_data: dict) -> AgentDiagnosis:
    system_prompt = """
    You are the Senior Production Technologist. 
    Your Goal: Identify wells with 'High Potential' for oil gain.
    
    Rules:
    1. Analyze 'current_rate' vs 'potential_rate'.
    2. If potential > current by 20%, recommend intervention.
    3. If water_cut > 90%, flag as 'High Risk' unless potential is massive.
    4. Ignore mechanical issues; that is not your department.
    """
    data_str = f"Well: {well_id}, Data: {well_data}"
    return run_llm_agent("Production Agent", system_prompt, data_str, AgentDiagnosis)

# --- 2. INTEGRITY AGENT (The Safety Veto) ---
def run_integrity_agent(well_id: str, well_data: dict) -> AgentDiagnosis:
    system_prompt = """
    You are the Well Integrity Specialist.
    Your Goal: Ensure safety and mechanical feasibility.
    
    CRITICAL INSTRUCTIONS:
    1. Scan the 'mechanical_issues' and 'casing_status' fields.
    2. If you see keywords like 'Collapsed', 'Leak', 'Restriction', 'Sand', or 'Corrosion':
       - You MUST set 'blocking_flag' to True.
       - Severity must be 'High'.
    3. If blocking_flag is True, your recommendation must be 'DO NOT INTERVENE' or 'RIG WORKOVER REQUIRED'.
    """
    data_str = f"Well: {well_id}, Data: {well_data}"
    return run_llm_agent("Integrity Agent", system_prompt, data_str, AgentDiagnosis)

# --- 3. MOTHER AGENT (The Orchestrator) ---
def run_mother_agent(well_id: str, prod_report: AgentDiagnosis, integ_report: AgentDiagnosis) -> WorkoverCandidate:
    system_prompt = """
    You are the Asset Manager. You receive reports from your Production and Integrity teams.
    You must make the final decision on the workover.

    CONFLICT RESOLUTION PROTOCOL:
    1. SAFETY FIRST: Look at the Integrity Agent's report FIRST.
       - If Integrity Agent has 'blocking_flag=True', the Decision MUST be 'NO GO'.
       - Explicitly state in 'technical_justification' that Integrity vetoed the job.
    
    2. ROI SECOND: If Integrity is clear (blocking_flag=False):
       - Look at Production Agent. If they recommend work, approve it.
       - Choose a 'proposed_job_type' based on the issue described.

    3. OUTPUT:
       - Generate a concise 'technical_justification' summarizing the trade-off.
    """
    
    context = f"""
    Target Well: {well_id}
    [REPORT 1: PRODUCTION TEAM]
    Recommendation: {prod_report.recommendation}
    Issue: {prod_report.issue_detected}
    Confidence: {prod_report.confidence_score}
    
    [REPORT 2: INTEGRITY TEAM]
    Recommendation: {integ_report.recommendation}
    Issue: {integ_report.issue_detected}
    Blocking Flag: {integ_report.blocking_flag}
    """
    
    return run_llm_agent("Mother Agent", system_prompt, context, WorkoverCandidate)