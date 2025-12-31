import os
import sqlite3
import logging
import threading
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
# Removed langchain.tools import as we're using regular functions now
import json
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Configuration class for database operations"""
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(self.project_root, "diseases.db")
        self.connection_timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

config = DatabaseConfig()

# Thread-local storage for database connections
_thread_local = threading.local()

@contextmanager
def get_db_connection():
    """Enhanced database connection manager with proper error handling"""
    connection = None
    try:
        # Check if connection exists in thread-local storage
        if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
            _thread_local.connection = sqlite3.connect(
                config.db_path,
                timeout=config.connection_timeout,
                check_same_thread=False
            )
            _thread_local.connection.row_factory = sqlite3.Row
            _thread_local.connection.execute("PRAGMA foreign_keys = ON")
        
        connection = _thread_local.connection
        yield connection
        connection.commit()
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            logger.warning(f"Database locked, retrying... {e}")
            raise
        else:
            logger.error(f"Database operational error: {e}")
            raise
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        # Don't close connection here - reuse thread-local connections
        pass

def close_thread_connection():
    """Close thread-local connection"""
    if hasattr(_thread_local, 'connection') and _thread_local.connection:
        _thread_local.connection.close()
        _thread_local.connection = None

def validate_database_schema():
    """Validate that required database schema exists"""
    required_tables = ['diseases', 'symptoms', 'disease_symptoms']
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            missing_tables = set(required_tables) - existing_tables
            if missing_tables:
                logger.warning(f"Missing database tables: {missing_tables}")
                return False
            
            # Check if tables have data
            for table in required_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count == 0:
                    logger.warning(f"Table {table} is empty")
            
            return True
            
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False

def execute_with_retry(operation_func, *args, **kwargs):
    """Execute database operation with retry logic"""
    for attempt in range(config.max_retries):
        try:
            return operation_func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < config.max_retries - 1:
                logger.warning(f"Database locked, attempt {attempt + 1}/{config.max_retries}")
                import time
                time.sleep(config.retry_delay * (attempt + 1))
                continue
            else:
                raise
        except Exception as e:
            if attempt < config.max_retries - 1:
                logger.warning(f"Operation failed, attempt {attempt + 1}/{config.max_retries}: {e}")
                import time
                time.sleep(config.retry_delay)
                continue
            else:
                raise
    
    raise Exception(f"Operation failed after {config.max_retries} attempts")

# Enhanced hospital data with more realistic information
ENHANCED_HOSPITAL_DATA = [
    # Apollo Hospital slots
    {"slot_id": 1, "hospital": "Apollo Hospital", "specialty": "General Physician", "doctor": "Dr. Sharma", "time": "2025-09-28 09:00", "duration": 30, "booked": False, "cost": 500},
    {"slot_id": 2, "hospital": "Apollo Hospital", "specialty": "General Physician", "doctor": "Dr. Patel", "time": "2025-09-28 10:00", "duration": 30, "booked": False, "cost": 500},
    {"slot_id": 3, "hospital": "Apollo Hospital", "specialty": "Dermatology", "doctor": "Dr. Kumar", "time": "2025-09-28 11:00", "duration": 30, "booked": False, "cost": 700},
    {"slot_id": 4, "hospital": "Apollo Hospital", "specialty": "Cardiology", "doctor": "Dr. Singh", "time": "2025-09-28 14:00", "duration": 45, "booked": True, "cost": 1000},
    
    # KIMS Hospital slots
    {"slot_id": 5, "hospital": "KIMS Hospital", "specialty": "General Physician", "doctor": "Dr. Reddy", "time": "2025-09-28 09:30", "duration": 30, "booked": False, "cost": 400},
    {"slot_id": 6, "hospital": "KIMS Hospital", "specialty": "Orthopedics", "doctor": "Dr. Rao", "time": "2025-09-28 15:00", "duration": 30, "booked": False, "cost": 800},
    {"slot_id": 7, "hospital": "KIMS Hospital", "specialty": "Emergency Medicine", "doctor": "Dr. Khan", "time": "2025-09-28 16:00", "duration": 30, "booked": False, "cost": 1200},
    
    # Government Hospital slots
    {"slot_id": 8, "hospital": "Government Hospital Warangal", "specialty": "General Physician", "doctor": "Dr. Prasad", "time": "2025-09-28 10:30", "duration": 20, "booked": False, "cost": 50},
    {"slot_id": 9, "hospital": "Government Hospital Warangal", "specialty": "General Physician", "doctor": "Dr. Nair", "time": "2025-09-28 11:30", "duration": 20, "booked": False, "cost": 50},
    {"slot_id": 10, "hospital": "Government Hospital Warangal", "specialty": "Emergency Medicine", "doctor": "Dr. Gupta", "time": "2025-09-28 12:00", "duration": 30, "booked": False, "cost": 100},
    
    # Future slots for next few days
    {"slot_id": 11, "hospital": "Apollo Hospital", "specialty": "General Physician", "doctor": "Dr. Sharma", "time": "2025-09-29 09:00", "duration": 30, "booked": False, "cost": 500},
    {"slot_id": 12, "hospital": "KIMS Hospital", "specialty": "Infectious Disease", "doctor": "Dr. Menon", "time": "2025-09-29 10:00", "duration": 45, "booked": False, "cost": 900},
]

def get_available_slots(hospital: str, specialty: str, date_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Find available appointment slots for a given hospital and specialty.
    Enhanced with better filtering, error handling, and comprehensive information.
    
    Args:
        hospital: Hospital name (case-insensitive, partial matches allowed)
        specialty: Medical specialty (case-insensitive, partial matches allowed)  
        date_filter: Optional date filter in YYYY-MM-DD format
    
    Returns:
        List of available appointment slots with comprehensive information
    """
    try:
        logger.info(f"Searching for slots at '{hospital}' for '{specialty}' specialty")
        
        if not hospital or not specialty:
            logger.error("Hospital and specialty parameters are required")
            return []
        
        # Normalize inputs
        hospital_lower = hospital.lower().strip()
        specialty_lower = specialty.lower().strip()
        
        available_slots = []
        
        for slot in ENHANCED_HOSPITAL_DATA:
            # Check if slot matches criteria
            hospital_match = (
                hospital_lower in slot["hospital"].lower() or
                slot["hospital"].lower().startswith(hospital_lower)
            )
            
            specialty_match = (
                specialty_lower in slot["specialty"].lower() or
                slot["specialty"].lower().startswith(specialty_lower)
            )
            
            # Date filtering
            date_match = True
            if date_filter:
                try:
                    slot_date = datetime.fromisoformat(slot["time"]).date()
                    filter_date = datetime.fromisoformat(date_filter).date()
                    date_match = slot_date == filter_date
                except ValueError:
                    logger.warning(f"Invalid date format: {date_filter}")
                    date_match = True
            
            # Check if slot is in the future
            slot_datetime = datetime.fromisoformat(slot["time"])
            is_future = slot_datetime > datetime.now()
            
            if hospital_match and specialty_match and not slot["booked"] and date_match and is_future:
                available_slots.append({
                    "slot_id": slot["slot_id"],
                    "hospital": slot["hospital"],
                    "specialty": slot["specialty"],
                    "doctor": slot["doctor"],
                    "appointment_time": slot["time"],
                    "duration_minutes": slot["duration"],
                    "consultation_fee": slot["cost"],
                    "available": True
                })
        
        logger.info(f"Found {len(available_slots)} available slots")
        
        # Sort by appointment time
        available_slots.sort(key=lambda x: x["appointment_time"])
        
        return available_slots
        
    except Exception as e:
        logger.error(f"Error searching for slots: {e}\n{traceback.format_exc()}")
        return []

def book_appointment(slot_id: int, patient_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Book an appointment by slot ID with comprehensive validation and confirmation.
    
    Args:
        slot_id: Unique identifier for the appointment slot
        patient_info: Optional patient information dictionary
    
    Returns:
        Dictionary with booking confirmation details or error information
    """
    try:
        logger.info(f"Attempting to book appointment for slot ID: {slot_id}")
        
        if not isinstance(slot_id, int) or slot_id <= 0:
            return {
                "success": False,
                "error": "Invalid slot ID provided",
                "slot_id": slot_id
            }
        
        # Find the slot
        target_slot = None
        for slot in ENHANCED_HOSPITAL_DATA:
            if slot["slot_id"] == slot_id:
                target_slot = slot
                break
        
        if not target_slot:
            logger.warning(f"Slot ID {slot_id} not found")
            return {
                "success": False,
                "error": f"Appointment slot {slot_id} not found",
                "slot_id": slot_id
            }
        
        # Check if already booked
        if target_slot["booked"]:
            logger.warning(f"Slot ID {slot_id} is already booked")
            return {
                "success": False,
                "error": f"Appointment slot {slot_id} is already booked",
                "slot_id": slot_id
            }
        
        # Check if appointment is in the future
        appointment_time = datetime.fromisoformat(target_slot["time"])
        if appointment_time <= datetime.now():
            logger.warning(f"Slot ID {slot_id} is in the past")
            return {
                "success": False,
                "error": f"Cannot book past appointment slot {slot_id}",
                "slot_id": slot_id
            }
        
        # Book the appointment
        target_slot["booked"] = True
        target_slot["booked_at"] = datetime.now().isoformat()
        
        if patient_info:
            target_slot["patient_info"] = patient_info
        
        logger.info(f"Successfully booked appointment slot {slot_id}")
        
        return {
            "success": True,
            "booking_confirmation": {
                "booking_id": f"BK{slot_id:04d}",
                "slot_id": slot_id,
                "hospital": target_slot["hospital"],
                "specialty": target_slot["specialty"],
                "doctor": target_slot["doctor"],
                "appointment_time": target_slot["time"],
                "duration": f"{target_slot['duration']} minutes",
                "consultation_fee": f"₹{target_slot['cost']}",
                "booked_at": target_slot["booked_at"],
                "status": "confirmed"
            },
            "instructions": {
                "arrival_time": "Please arrive 15 minutes before your appointment",
                "documents_required": ["Valid ID", "Previous medical records if any"],
                "contact_number": "For rescheduling: +91-8712345678",
                "cancellation_policy": "Cancel at least 2 hours before appointment"
            }
        }
        
    except Exception as e:
        logger.error(f"Error booking appointment: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Booking system error: {str(e)}",
            "slot_id": slot_id
        }

def cancel_appointment(slot_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Cancel a booked appointment.
    
    Args:
        slot_id: Unique identifier for the appointment slot
        reason: Optional reason for cancellation
    
    Returns:
        Dictionary with cancellation confirmation or error information
    """
    try:
        logger.info(f"Attempting to cancel appointment for slot ID: {slot_id}")
        
        # Find the slot
        target_slot = None
        for slot in ENHANCED_HOSPITAL_DATA:
            if slot["slot_id"] == slot_id:
                target_slot = slot
                break
        
        if not target_slot:
            return {
                "success": False,
                "error": f"Appointment slot {slot_id} not found"
            }
        
        if not target_slot["booked"]:
            return {
                "success": False,
                "error": f"Appointment slot {slot_id} is not currently booked"
            }
        
        # Cancel the appointment
        target_slot["booked"] = False
        target_slot["cancelled_at"] = datetime.now().isoformat()
        if reason:
            target_slot["cancellation_reason"] = reason
        
        # Remove patient info for privacy
        target_slot.pop("patient_info", None)
        
        logger.info(f"Successfully cancelled appointment slot {slot_id}")
        
        return {
            "success": True,
            "cancellation_confirmation": {
                "slot_id": slot_id,
                "hospital": target_slot["hospital"],
                "specialty": target_slot["specialty"],
                "original_time": target_slot["time"],
                "cancelled_at": target_slot["cancelled_at"],
                "status": "cancelled"
            }
        }
        
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return {
            "success": False,
            "error": f"Cancellation system error: {str(e)}"
        }

def find_diseases_by_symptoms(symptoms_list: List[str]) -> Dict[str, Any]:
    """
    Enhanced disease lookup by symptoms with comprehensive error handling and fuzzy matching.
    
    Args:
        symptoms_list: List of symptom names to match
    
    Returns:
        Dictionary containing matched diseases and metadata
    """
    try:
        logger.info(f"Searching for diseases matching symptoms: {symptoms_list}")
        
        if not symptoms_list or not isinstance(symptoms_list, list):
            logger.warning("No symptoms provided or invalid format")
            return {
                "diseases": [],
                "matched_symptoms": [],
                "total_matches": 0,
                "error": "No symptoms provided"
            }
        
        # Clean and normalize symptoms
        cleaned_symptoms = [symptom.strip().lower() for symptom in symptoms_list if symptom.strip()]
        
        if not cleaned_symptoms:
            return {
                "diseases": [],
                "matched_symptoms": [],
                "total_matches": 0,
                "error": "No valid symptoms after cleaning"
            }
        
        def search_diseases():
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First, check if database has the required tables
                if not validate_database_schema():
                    logger.error("Database schema validation failed")
                    return [], []
                
                # Find exact symptom matches
                placeholders = ', '.join('?' for _ in cleaned_symptoms)
                
                # Query for diseases that match any of the symptoms
                query = f"""
                    SELECT d.name as disease_name, 
                           GROUP_CONCAT(s.name) as matched_symptoms,
                           COUNT(DISTINCT s.name) as symptom_count
                    FROM diseases d
                    JOIN disease_symptoms ds ON d.disease_id = ds.disease_id
                    JOIN symptoms s ON ds.symptom_id = s.symptom_id
                    WHERE LOWER(s.name) IN ({placeholders})
                    GROUP BY d.name
                    ORDER BY symptom_count DESC, d.name
                """
                
                cursor.execute(query, cleaned_symptoms)
                exact_matches = cursor.fetchall()
                
                # Also try fuzzy matching for partial symptom names
                fuzzy_matches = []
                if not exact_matches:
                    fuzzy_query = """
                        SELECT d.name as disease_name, 
                               GROUP_CONCAT(s.name) as matched_symptoms,
                               COUNT(DISTINCT s.name) as symptom_count
                        FROM diseases d
                        JOIN disease_symptoms ds ON d.disease_id = ds.disease_id
                        JOIN symptoms s ON ds.symptom_id = s.symptom_id
                        WHERE """ + " OR ".join([f"LOWER(s.name) LIKE '%{symptom}%'" for symptom in cleaned_symptoms]) + """
                        GROUP BY d.name
                        ORDER BY symptom_count DESC, d.name
                        LIMIT 10
                    """
                    
                    cursor.execute(fuzzy_query)
                    fuzzy_matches = cursor.fetchall()
                
                return exact_matches, fuzzy_matches
        
        # Execute with retry logic
        exact_results, fuzzy_results = execute_with_retry(search_diseases)
        
        # Process results
        diseases = []
        matched_symptoms = set()
        
        # Process exact matches first
        for row in exact_results:
            symptoms_for_disease = [s.strip() for s in row[1].split(',')]
            matched_symptoms.update(symptoms_for_disease)
            diseases.append({
                "name": row[0],
                "matched_symptoms": symptoms_for_disease,
                "symptom_match_count": row[2],
                "match_type": "exact"
            })
        
        # Add fuzzy matches if no exact matches found
        if not exact_results and fuzzy_results:
            for row in fuzzy_results:
                symptoms_for_disease = [s.strip() for s in row[1].split(',')]
                matched_symptoms.update(symptoms_for_disease)
                diseases.append({
                    "name": row[0],
                    "matched_symptoms": symptoms_for_disease,
                    "symptom_match_count": row[2],
                    "match_type": "partial"
                })
        
        result = {
            "diseases": diseases,
            "matched_symptoms": list(matched_symptoms),
            "total_matches": len(diseases),
            "search_symptoms": cleaned_symptoms,
            "database_status": "connected"
        }
        
        if not diseases:
            result["message"] = "No diseases found matching the provided symptoms. Consider consulting a healthcare professional for accurate diagnosis."
        
        logger.info(f"Found {len(diseases)} diseases matching symptoms")
        return result
        
    except sqlite3.OperationalError as e:
        error_msg = f"Database error: {str(e)}"
        if "no such table" in str(e).lower():
            error_msg += ". Please ensure the database is properly initialized by running the setup script."
        
        logger.error(error_msg)
        return {
            "diseases": [],
            "matched_symptoms": [],
            "total_matches": 0,
            "error": error_msg,
            "database_status": "error"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in disease search: {e}\n{traceback.format_exc()}")
        return {
            "diseases": [],
            "matched_symptoms": [],
            "total_matches": 0,
            "error": f"System error: {str(e)}",
            "database_status": "error"
        }

def get_hospital_info(hospital_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get comprehensive information about hospitals and their available services.
    
    Args:
        hospital_name: Optional specific hospital name to filter by
    
    Returns:
        List of hospitals with their information
    """
    try:
        hospitals = {}
        
        # Aggregate information from slot data
        for slot in ENHANCED_HOSPITAL_DATA:
            hospital = slot["hospital"]
            if hospital not in hospitals:
                hospitals[hospital] = {
                    "name": hospital,
                    "specialties": set(),
                    "doctors": set(),
                    "available_slots": 0,
                    "price_range": {"min": float('inf'), "max": 0}
                }
            
            hospitals[hospital]["specialties"].add(slot["specialty"])
            hospitals[hospital]["doctors"].add(slot["doctor"])
            
            if not slot["booked"]:
                hospitals[hospital]["available_slots"] += 1
            
            hospitals[hospital]["price_range"]["min"] = min(hospitals[hospital]["price_range"]["min"], slot["cost"])
            hospitals[hospital]["price_range"]["max"] = max(hospitals[hospital]["price_range"]["max"], slot["cost"])
        
        # Convert to list format
        result = []
        for hospital_name_key, info in hospitals.items():
            if hospital_name and hospital_name.lower() not in hospital_name_key.lower():
                continue
                
            result.append({
                "name": info["name"],
                "available_specialties": list(info["specialties"]),
                "number_of_doctors": len(info["doctors"]),
                "available_appointment_slots": info["available_slots"],
                "consultation_fee_range": {
                    "min": f"₹{info['price_range']['min']}",
                    "max": f"₹{info['price_range']['max']}"
                },
                "contact_info": {
                    "phone": "+91-8712345678",
                    "emergency": "108"
                }
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting hospital info: {e}")
        return []

def get_appointment_history(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get appointment history (mock implementation for demonstration).
    
    Args:
        patient_id: Optional patient identifier
    
    Returns:
        List of appointment history records
    """
    try:
        # Mock implementation - in real system would query actual patient database
        history = []
        
        for slot in ENHANCED_HOSPITAL_DATA:
            if slot.get("booked") and slot.get("booked_at"):
                history.append({
                    "appointment_id": f"BK{slot['slot_id']:04d}",
                    "hospital": slot["hospital"],
                    "specialty": slot["specialty"],
                    "doctor": slot["doctor"],
                    "appointment_time": slot["time"],
                    "booked_at": slot["booked_at"],
                    "status": "cancelled" if slot.get("cancelled_at") else "confirmed",
                    "consultation_fee": f"₹{slot['cost']}"
                })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting appointment history: {e}")
        return []

# Utility functions for testing and maintenance
def test_database_connection():
    """Test database connectivity and schema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            logger.info(f"Database connection successful. Found {table_count} tables.")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def reset_mock_appointments():
    """Reset all appointments to unbooked state (for testing)"""
    global ENHANCED_HOSPITAL_DATA
    for slot in ENHANCED_HOSPITAL_DATA:
        slot["booked"] = False
        slot.pop("booked_at", None)
        slot.pop("cancelled_at", None)
        slot.pop("patient_info", None)
    
    logger.info("All mock appointments reset to available state")

if __name__ == "__main__":
    # Test the enhanced functionality
    print("Testing SQL Tools:")
    print("1. Database Connection Test:")
    print(test_database_connection())
    
    print("\n2. Hospital Info Test:")
    hospitals = get_hospital_info()
    print(json.dumps(hospitals, indent=2))
    
    print("\n3. Available Slots Test:")
    slots = get_available_slots("Apollo", "General")
    print(json.dumps(slots, indent=2))
    
    print("\n4. Disease Search Test:")
    diseases = find_diseases_by_symptoms(["fever", "headache"])
    print(json.dumps(diseases, indent=2))