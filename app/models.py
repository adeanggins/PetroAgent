from pydantic import BaseModel
from typing import Optional

# 1. Output from Diagnostic Agents (Prod & Integrity)
class AgentDiagnosis(BaseModel):
    well_id: Optional[str] = None
    agent_name: str
    issue_detected: str
    recommendation: str
    severity: str  # e.g., "High", "Medium", "Low"
    blocking_flag: bool # The Veto Power Switch
    confidence_score: float

# 2. Output from Mother Agent (The Decision)
class WorkoverCandidate(BaseModel):
    well_id: str
    proposed_job_type: str # e.g., "Acid Stimulation", "NO GO"
    technical_justification: str
    integrity_block: bool
    execution_date: str = "TBD"
    source: str = "AI" 

# 3. Output for Execution (Optional, but good to have)
class ExecutionPlan(BaseModel):
    well_id: str
    estimated_cost: float
    schedule_start_day: int
    resource_status: str
    final_approval: bool