from typing import Dict, Any
from langchain.tools import tool

@tool
def save_consultation_details(details: Dict[str, Any]) -> str:
    """
    Persist consultation details (stub). Returns a confirmation string.
    Replace with real MongoDB logic if needed.
    """
    print("[mongo_tools] Saved consultation details:", details)
    return "saved"


