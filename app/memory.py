import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models import WorkoverCandidate  # <--- FIXED IMPORT

class MemoryBank:
    def __init__(self, filename: str = "data/workover_memory.json", retention_days: int = 7):
        """
        Initialize the Memory Bank.
        """
        self.filename = filename
        self.retention_days = retention_days
        
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        """Loads the JSON database into a Python dictionary."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Memory file corrupted. Starting fresh.")
                return {}
        return {}

    def _save_to_disk(self):
        """Writes the current memory state to the JSON file."""
        with open(self.filename, 'w') as f:
            json.dump(self.memory, f, indent=4)

    def save_decision(self, well_id: str, decision: WorkoverCandidate):
        """
        Saves a WorkoverCandidate object to memory with a timestamp.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "well_id": well_id,
            "data": decision.model_dump() 
        }
        
        self.memory[well_id] = entry
        self._save_to_disk()
        print(f"💾 [Memory] Saved decision for {well_id}.")

    def recall(self, well_id: str) -> Optional[WorkoverCandidate]:
        """
        Retrieves a decision if it exists and is not expired.
        """
        if well_id not in self.memory:
            return None

        record = self.memory[well_id]
        stored_time_str = record.get("timestamp")
        
        if not stored_time_str:
            return None

        stored_time = datetime.fromisoformat(stored_time_str)
        expiry_time = stored_time + timedelta(days=self.retention_days)

        # Check if memory has expired
        if datetime.now() > expiry_time:
            print(f"♻️ [Memory] Record for {well_id} expired. Re-analyzing.")
            return None

        print(f"⚡ [Memory] Cache Hit for {well_id}.")
        return WorkoverCandidate(**record["data"])

    def get_stats(self):
        """Returns statistics for the dashboard."""
        return {
            "total_records": len(self.memory),
            "last_update": datetime.now().strftime("%H:%M:%S")
        }