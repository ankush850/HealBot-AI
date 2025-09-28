import os
import logging
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
import traceback
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, CommaSeparatedListOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException
from openai import RateLimitError, APIError

# Import tools with error handling - FIXED
try:
    # Import the actual tool functions, not the langchain tools
    import sys
    sys.path.append('.')  # Add current directory to path
    
    from tools.sql_tools import (
        get_available_slots, 
        book_appointment, 
        find_diseases_by_symptoms,
        get_hospital_info
    )
    
    # Try importing mongo tools if available
    try:
        from tools.mongo_tools import save_consultation_details
    except ImportError:
        logging.warning("mongo_tools not found, creating mock function")
        def save_consultation_details(data):
            logging.info(f"Mock save consultation: {data}")
            return {"status": "mock_saved"}
        
except ImportError as e:
    logging.error(f"Failed to import tools: {e}")
    # Create mock functions for testing
    def get_available_slots(hospital: str, specialty: str, date_filter: Optional[str] = None):
        return []
    
    def book_appointment(slot_id: int, patient_info: Optional[Dict] = None):
        return {"success": False, "error": "Tools not available"}
    
    def find_diseases_by_symptoms(symptoms_list: List[str]):
        return {"diseases": [], "matched_symptoms": []}
    
    def save_consultation_details(data):
        return {"status": "mock_saved"}

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BookingState(TypedDict):
    user_query: str
    symptoms: List[str]
    urgency: str
    specialty: str
    potential_diseases: List[Dict[str, Any]]  # FIXED: should be list of dicts
    available_slots: List[dict]
    final_response: str
    error_message: Optional[str]
    retry_count: int
    processing_timestamp: str

class BookingConfig:
    """Configuration class for booking agent"""
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "gpt-4o")
        self.temperature = float(os.getenv("MODEL_TEMPERATURE", "0"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.timeout_seconds = int(os.getenv("REQUEST_TIMEOUT", "30"))
        
        # Validate required environment variables
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found, using mock mode")

config = BookingConfig()

# Initialize LLM with robust configuration - FIXED
try:
    if config.openai_api_key:
        llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            request_timeout=config.timeout_seconds,
            max_retries=config.max_retries
        )
        logger.info(f"Initialized LLM with model: {config.model_name}")
    else:
        # Mock LLM for testing without API key
        class MockLLM:
            def invoke(self, input_data):
                if "symptoms" in str(input_data):
                    return ["fever", "headache"]
                elif "urgency" in str(input_data):
                    return {"urgency": "Medium", "specialty": "General Physician"}
                return "Mock response"
        
        llm = MockLLM()
        logger.info("Using mock LLM - no API key provided")
        
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    raise

# Initialize parsers with error handling
classification_parser = JsonOutputParser()
symptom_parser = CommaSeparatedListOutputParser()

def validate_state(state: BookingState) -> bool:
    """Validate that the state contains required fields"""
    required_fields = ['user_query']
    for field in required_fields:
        if field not in state or not state[field]:
            logger.error(f"Missing required field: {field}")
            return False
    return True

def initialize_state_defaults(state: BookingState) -> BookingState:
    """Initialize default values for state fields"""
    defaults = {
        'symptoms': [],
        'urgency': '',
        'specialty': '',
        'potential_diseases': [],
        'available_slots': [],
        'final_response': '',
        'error_message': None,
        'retry_count': 0,
        'processing_timestamp': datetime.now().isoformat()
    }
    
    for key, default_value in defaults.items():
        if key not in state:
            state[key] = default_value
    
    return state

def handle_llm_error(func):
    """Decorator to handle LLM-related errors"""
    def wrapper(state: BookingState) -> BookingState:
        try:
            return func(state)
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded in {func.__name__}: {e}")
            state['error_message'] = "Service temporarily unavailable due to high demand. Please try again later."
            return state
        except APIError as e:
            logger.error(f"API error in {func.__name__}: {e}")
            state['error_message'] = "Unable to process request due to service error. Please try again."
            return state
        except OutputParserException as e:
            logger.error(f"Output parsing error in {func.__name__}: {e}")
            state['error_message'] = "Error processing response. Please rephrase your request."
            return state
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}\n{traceback.format_exc()}")
            state['error_message'] = "An unexpected error occurred. Please try again."
            return state
    return wrapper

@handle_llm_error
def extract_symptoms_node(state: BookingState) -> BookingState:
    """Extract medical symptoms from user query with enhanced validation"""
    logger.info("Starting symptom extraction")
    
    if not validate_state(state):
        state['error_message'] = "Invalid input provided"
        return state
    
    state = initialize_state_defaults(state)
    
    try:
        # Enhanced prompt for better symptom extraction
        prompt = ChatPromptTemplate.from_template(
            """Extract key medical symptoms from the following text. 
            Focus on physical symptoms, pain descriptions, and medical conditions mentioned.
            Ignore non-medical complaints like scheduling preferences.
            Respond with a comma-separated list of symptoms only.
            If no medical symptoms are found, respond with "none".
            
            Text: {query}
            
            Symptoms:"""
        )
        
        chain = prompt | llm | symptom_parser
        symptoms_list = chain.invoke({"query": state['user_query']})
        
        # Clean and validate symptoms
        if symptoms_list and symptoms_list != ["none"]:
            state['symptoms'] = [s.strip().capitalize() for s in symptoms_list if s.strip()]
            logger.info(f"Extracted symptoms: {state['symptoms']}")
        else:
            state['symptoms'] = []
            logger.info("No symptoms extracted from user query")
    
    except Exception as e:
        logger.error(f"Error in symptom extraction: {e}")
        # Fallback: simple keyword extraction
        common_symptoms = ['fever', 'headache', 'cough', 'pain', 'nausea', 'fatigue']
        found_symptoms = []
        query_lower = state['user_query'].lower()
        for symptom in common_symptoms:
            if symptom in query_lower:
                found_symptoms.append(symptom.capitalize())
        state['symptoms'] = found_symptoms
    
    return state

@handle_llm_error
def classify_issue_node(state: BookingState) -> BookingState:  # FIXED: return BookingState
    """Classify medical issue urgency and specialty with validation"""
    logger.info("Starting issue classification")
    
    if not state.get('symptoms'):
        logger.warning("No symptoms to classify")
        state['urgency'] = "Low"
        state['specialty'] = "General Physician"
        return state
    
    try:
        # Enhanced classification prompt
        prompt = ChatPromptTemplate.from_template(
            """Analyze the following symptoms and classify them into urgency level and medical specialty.
            
            Urgency levels (choose exactly one):
            - "Emergency": Life-threatening symptoms requiring immediate attention
            - "High": Severe symptoms requiring urgent care within 24 hours
            - "Medium": Concerning symptoms requiring care within a few days
            - "Low": Minor symptoms that can wait for routine care
            
            Medical specialties (choose the most appropriate one):
            - "Cardiology": Heart and cardiovascular issues
            - "Dermatology": Skin, hair, and nail conditions
            - "General Physician": General health issues, infections, common ailments
            - "Orthopedics": Bone, joint, and muscle problems
            - "Emergency": For emergency cases requiring immediate attention
            
            Respond with a JSON object containing exactly these keys: "urgency" and "specialty".
            
            Symptoms: {symptoms}
            
            Classification:"""
        )
        
        chain = prompt | llm | classification_parser
        classification = chain.invoke({"symptoms": ", ".join(state['symptoms'])})
        
        # Validate classification results
        valid_urgencies = ["Emergency", "High", "Medium", "Low"]
        valid_specialties = ["Cardiology", "Dermatology", "General Physician", "Orthopedics", "Emergency"]
        
        urgency = classification.get('urgency', 'Low')
        specialty = classification.get('specialty', 'General Physician')
        
        if urgency not in valid_urgencies:
            logger.warning(f"Invalid urgency '{urgency}', defaulting to 'Low'")
            urgency = 'Low'
        
        if specialty not in valid_specialties:
            logger.warning(f"Invalid specialty '{specialty}', defaulting to 'General Physician'")
            specialty = 'General Physician'
        
        state['urgency'] = urgency
        state['specialty'] = specialty
        
        logger.info(f"Classification - Urgency: {urgency}, Specialty: {specialty}")
    
    except Exception as e:
        logger.error(f"Error in classification: {e}")
        state['urgency'] = "Medium"
        state['specialty'] = "General Physician"
    
    return state

def find_potential_diseases_node(state: BookingState) -> BookingState:
    """Find potential diseases based on symptoms with error handling"""
    logger.info("Finding potential diseases")
    
    try:
        if not state.get('symptoms'):
            logger.info("No symptoms provided for disease matching")
            state['potential_diseases'] = []
            return state
        
        # FIXED: Call function directly, not as langchain tool
        diseases_result = find_diseases_by_symptoms(state['symptoms'])
        
        if isinstance(diseases_result, dict) and 'diseases' in diseases_result:
            state['potential_diseases'] = diseases_result['diseases']
        else:
            state['potential_diseases'] = []
            
        logger.info(f"Found {len(state['potential_diseases'])} potential diseases")
        
    except Exception as e:
        logger.error(f"Error finding potential diseases: {e}")
        state['potential_diseases'] = []
        state['error_message'] = "Unable to match symptoms with conditions at this time."
    
    return state

def present_findings_node(state: BookingState) -> BookingState:
    """Present findings with comprehensive error handling and formatting"""
    logger.info("Presenting findings report")
    
    try:
        report_parts = ["### Pre-Consultation Summary"]
        
        # Add symptoms section
        if state.get('symptoms'):
            symptoms_text = ', '.join(state['symptoms'])
            report_parts.append(f"- **Symptoms Reported**: {symptoms_text}")
        else:
            report_parts.append("- **Symptoms Reported**: None specified")
        
        # Add urgency and specialty
        urgency = state.get('urgency', 'Unknown')
        specialty = state.get('specialty', 'General Physician')
        report_parts.extend([
            f"- **Urgency Level**: {urgency}",
            f"- **Recommended Specialty**: {specialty}"
        ])
        
        # Add potential conditions if found - FIXED
        if state.get('potential_diseases'):
            if isinstance(state['potential_diseases'], list) and len(state['potential_diseases']) > 0:
                disease_names = []
                for disease in state['potential_diseases']:
                    if isinstance(disease, dict) and 'name' in disease:
                        disease_names.append(disease['name'])
                    elif isinstance(disease, str):
                        disease_names.append(disease)
                
                if disease_names:
                    diseases_text = ', '.join(disease_names)
                    report_parts.append(f"- **Potential Conditions**: {diseases_text}")
        
        # Add disclaimers and next steps
        report_parts.extend([
            "",
            "**Important Disclaimers:**",
            "• This is not a medical diagnosis",
            "• Always consult with a qualified healthcare professional",
            "• In case of emergency, call local emergency services immediately",
            "",
            "Would you like me to find available appointments? Reply with **'yes, find an appointment'** to continue."
        ])
        
        state['final_response'] = "\n".join(report_parts)
        logger.info("Successfully generated findings report")
        
    except Exception as e:
        logger.error(f"Error presenting findings: {e}")
        state['final_response'] = "Unable to generate report. Please try again."
        state['error_message'] = "Error generating consultation summary."
    
    return state

def find_slots_node(state: BookingState) -> BookingState:
    """Find available appointment slots with robust error handling"""
    logger.info("Finding available appointment slots")
    
    try:
        specialty = state.get('specialty', 'General Physician')
        hospital = os.getenv('DEFAULT_HOSPITAL', 'Apollo Hospital')
        
        # FIXED: Call function directly with proper parameters
        slots = get_available_slots(hospital, specialty)
        
        state['available_slots'] = slots or []
        logger.info(f"Found {len(state['available_slots'])} available slots")
        
        if not state['available_slots']:
            logger.warning(f"No slots found for {specialty} at {hospital}")
        
    except Exception as e:
        logger.error(f"Error finding appointment slots: {e}")
        state['available_slots'] = []
        state['error_message'] = "Unable to check appointment availability."
    
    return state

def book_appointment_node(state: BookingState) -> BookingState:
    """Book appointment with comprehensive validation and error handling"""
    logger.info("Attempting to book appointment")
    
    try:
        if not state.get('available_slots'):
            state['final_response'] = "No available slots to book."
            return state
        
        slot_to_book = state['available_slots'][0]
        
        # Validate slot data
        required_slot_fields = ['slot_id', 'hospital', 'specialty']
        for field in required_slot_fields:
            if field not in slot_to_book:
                raise ValueError(f"Invalid slot data: missing {field}")
        
        # FIXED: Call function directly with proper parameter
        result = book_appointment(slot_to_book['slot_id'])
        
        # Check if booking was successful
        if isinstance(result, dict) and result.get('success'):
            confirmation = result.get('booking_confirmation', {})
            
            # Generate confirmation
            confirmation_parts = [
                "### Appointment Successfully Booked!",
                "",
                f"**Booking Details:**",
                f"• **Booking ID**: {confirmation.get('booking_id', slot_to_book['slot_id'])}",
                f"• **Hospital**: {confirmation.get('hospital', slot_to_book['hospital'])}",
                f"• **Department**: {confirmation.get('specialty', slot_to_book['specialty'])}",
                f"• **Scheduled Time**: {confirmation.get('appointment_time', slot_to_book.get('appointment_time', 'TBD'))}",
                f"• **Confirmation**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "**Important Notes:**",
                "• Please arrive 15 minutes before your appointment",
                "• Bring a valid ID and any relevant medical records",
                "• Contact the hospital if you need to reschedule",
                "",
                "**Next Steps:**",
                "• You will receive a confirmation SMS/email shortly",
                "• Save this booking ID for your records"
            ]
            
            state['final_response'] = "\n".join(confirmation_parts)
            logger.info(f"Successfully booked appointment with ID: {slot_to_book['slot_id']}")
        else:
            error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
            state['final_response'] = f"Failed to book appointment: {error_msg}"
            state['error_message'] = "Booking failed"
        
        # Save consultation details if available - FIXED
        try:
            consultation_data = {
                'symptoms': state.get('symptoms', []),
                'urgency': state.get('urgency', ''),
                'specialty': state.get('specialty', ''),
                'potential_diseases': state.get('potential_diseases', []),
                'booking_id': slot_to_book['slot_id'],
                'timestamp': datetime.now().isoformat()
            }
            save_consultation_details(consultation_data)
            logger.info("Consultation details saved successfully")
        except Exception as save_error:
            logger.error(f"Failed to save consultation details: {save_error}")
            # Don't fail the booking if saving fails
        
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        state['final_response'] = "Failed to book appointment. Please try again or contact the hospital directly."
        state['error_message'] = "Booking system error occurred."
    
    return state

def emergency_protocol_node(state: BookingState) -> BookingState:
    """Handle emergency cases with appropriate messaging"""
    logger.warning("Emergency protocol activated")
    
    emergency_message = [
        "**EMERGENCY ALERT**",
        "",
        "Your symptoms may indicate a medical emergency that requires immediate attention.",
        "",
        "**Please take these actions immediately:**",
        "• Call emergency services: 108 (India)",
        "• Go to the nearest emergency room",
        "• Contact your nearest hospital directly",
        "",
        "**Emergency Hospitals in Warangal:**",
        "• Apollo Hospital Emergency: +91-xxx-xxx-xxxx",
        "• KIMS Hospital Emergency: +91-xxx-xxx-xxxx",
        "",
        "**Do not wait for an appointment booking in emergency situations.**"
    ]
    
    state['final_response'] = "\n".join(emergency_message)
    logger.info("Emergency protocol message generated")
    return state

def no_slots_found_node(state: BookingState) -> BookingState:
    """Handle cases when no appointment slots are available"""
    logger.info("No slots available - generating alternative options")
    
    no_slots_message = [
        "**No Available Appointments**",
        "",
        "Unfortunately, there are no available appointment slots at this time.",
        "",
        "**Alternative Options:**",
        "• Try again in a few hours as new slots may become available",
        "• Contact the hospital directly for urgent cases",
        "• Consider visiting a walk-in clinic",
        "• Check with other hospitals in the area",
        "",
        "**Hospital Contact Information:**",
        "• Apollo Hospital: +91-xxx-xxx-xxxx",
        "• KIMS Hospital: +91-xxx-xxx-xxxx",
        "",
        "We apologize for the inconvenience and recommend trying again later."
    ]
    
    state['final_response'] = "\n".join(no_slots_message)
    logger.info("No slots message generated")
    return state

def error_handler_node(state: BookingState) -> BookingState:
    """Handle system errors gracefully"""
    logger.error(f"Error handler activated: {state.get('error_message', 'Unknown error')}")
    
    error_message = [
        "**System Error**",
        "",
        "We encountered an issue processing your request.",
        state.get('error_message', 'An unexpected error occurred.'),
        "",
        "**Please try:**",
        "• Rephrasing your request",
        "• Trying again in a few minutes",
        "• Contacting support if the problem persists",
        "",
        "We apologize for the inconvenience."
    ]
    
    state['final_response'] = "\n".join(error_message)
    return state

# Enhanced conditional functions with error handling
def decide_after_classification(state: BookingState) -> str:
    """Decide next step after classification with error handling"""
    try:
        if state.get('error_message'):
            return "error_handler"
        
        urgency = state.get('urgency', '').lower()
        if urgency == "emergency":
            return "emergency"
        return "find_potential_diseases"
    
    except Exception as e:
        logger.error(f"Error in classification decision: {e}")
        return "error_handler"

def decide_after_finding_slots(state: BookingState) -> str:
    """Decide next step after finding slots"""
    try:
        if state.get('error_message'):
            return "error_handler"
        
        if not state.get('available_slots'):
            return "no_slots"
        return "book_slot"
    
    except Exception as e:
        logger.error(f"Error in slots decision: {e}")
        return "no_slots"

# Assemble the enhanced workflow graph
def create_booking_workflow() -> StateGraph:
    """Create and configure the booking workflow with error handling"""
    try:
        workflow = StateGraph(BookingState)
        
        # Add all nodes
        nodes = {
            "extract_symptoms": extract_symptoms_node,
            "classify_issue": classify_issue_node,
            "find_potential_diseases": find_potential_diseases_node,
            "present_findings": present_findings_node,
            "find_slots": find_slots_node,
            "book_appointment": book_appointment_node,
            "emergency_protocol": emergency_protocol_node,
            "no_slots_found": no_slots_found_node,
            "error_handler": error_handler_node
        }
        
        for name, node in nodes.items():
            workflow.add_node(name, node)
        
        # Configure workflow edges
        workflow.set_entry_point("extract_symptoms")
        workflow.add_edge("extract_symptoms", "classify_issue")
        
        workflow.add_conditional_edges(
            "classify_issue", 
            decide_after_classification, 
            {
                "emergency": "emergency_protocol",
                "find_potential_diseases": "find_potential_diseases",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_edge("find_potential_diseases", "present_findings")
        workflow.add_edge("present_findings", END)
        workflow.add_edge("emergency_protocol", END)
        workflow.add_edge("error_handler", END)
        
        # Booking continuation workflow
        workflow.add_node("continue_booking", find_slots_node)
        workflow.add_conditional_edges(
            "continue_booking", 
            decide_after_finding_slots, 
            {
                "no_slots": "no_slots_found",
                "book_slot": "book_appointment",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_edge("book_appointment", END)
        workflow.add_edge("no_slots_found", END)
        
        logger.info("Booking workflow created successfully")
        return workflow
        
    except Exception as e:
        logger.error(f"Failed to create booking workflow: {e}")
        raise

# Create the booking agent application
try:
    booking_agent_app = create_booking_workflow().compile()
    logger.info("Booking agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize booking agent: {e}")
    booking_agent_app = None

# Test functionality
def test_booking_system():
    """Test the booking system functionality"""
    try:
        print("Testing booking functionality...")
        
        # Test direct function calls
        slots = get_available_slots("Apollo Hospital", "General Physician")
        print(f"Available slots: {len(slots)}")
        
        if slots:
            slot_id = slots[0]['slot_id']
            print(f"Trying to book slot {slot_id}")
            result = book_appointment(slot_id)
            print(f"Booking result: {result}")
        
        # Test disease lookup
        diseases = find_diseases_by_symptoms(["fever", "headache"])
        print(f"Disease lookup result: {diseases}")
        
        return True
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_booking_system()