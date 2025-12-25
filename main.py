from fastapi import Request
from tools.whatsapp_tools import send_whatsapp_template
from fastapi import FastAPI  # Ensure FastAPI is imported

app = FastAPI()  # Initialize the FastAPI app

# WhatsApp Webhook Endpoint
@app.post("/webhook/whatsapp", tags=["Integration"])
async def whatsapp_webhook(request: Request):
    """
    Receives WhatsApp messages via webhook, processes them, and replies back on WhatsApp.
    """
    try:
        data = await request.json()
        # Extract message text and sender number (adjust keys as per WhatsApp webhook format)
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])
        if not messages or not messages[0]:
            return {"status": "no message found"}
        message = messages[0]
        user_text = message.get("text", {}).get("body", "")
        sender_number = message.get("from", "")
        # Use sender_number as session_id for simplicity
        session_id = sender_number
        # Call existing backend workflow (chat_with_agent)
        from pydantic import ValidationError
        try:
            user_query = UserQuery(query=user_text, session_id=session_id)
        except ValidationError as ve:
            return {"error": "Invalid input", "details": str(ve)}
        agent_response = await chat_with_agent(user_query)
        # Send backend output as a WhatsApp message (free text, not just template)
        reply_text = agent_response.response if hasattr(agent_response, "response") else str(agent_response)
        # Use a custom function for free text (assume send_whatsapp_text exists or fallback to template if not)
        try:
            from tools.whatsapp_tools import send_whatsapp_text
            send_result = send_whatsapp_text(sender_number, reply_text)
        except ImportError:
            # Fallback to template if free text sender is not implemented
            send_result = send_whatsapp_template(sender_number, template_name="hello_world", language_code="en_US")
        return {"status": "processed", "user": sender_number, "input": user_text, "output": reply_text, "whatsapp_result": send_result}
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return {"error": str(e)}
import os
import logging
import traceback
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import uvicorn
from dotenv import load_dotenv

# Import agents with error handling
try:
    from agents.health_adviser import health_adviser_app
    from agents.booking_agent import booking_agent_app, BookingState
    from agents.emergency_agent import emergency_agent_app, EmergencyState
except ImportError as e:
    logging.error(f"Failed to import agents: {e}")
    raise

# Add emergency system imports with error handling
try:
    from agents.emergency_agent import emergency_system, format_alert_for_display, emergency_agent_app, EmergencyState
    EMERGENCY_SYSTEM_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Emergency system not available: {e}")
    EMERGENCY_SYSTEM_AVAILABLE = False
    emergency_system = None

# Load environment variables
load_dotenv()

# Global emergency mode flag
EMERGENCY_MODE_ACTIVE = False

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APIConfig:
    """Configuration class for API settings"""
    def __init__(self):
        self.host = os.getenv('API_HOST', '0.0.0.0')
        self.port = int(os.getenv('API_PORT', '8000'))
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.max_session_age = int(os.getenv('MAX_SESSION_AGE_HOURS', '24'))
        self.max_sessions = int(os.getenv('MAX_SESSIONS', '10000'))
        self.rate_limit_requests = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
        self.rate_limit_window = int(os.getenv('RATE_LIMIT_WINDOW_MINUTES', '60'))
        
        # CORS settings
        self.cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
        self.cors_methods = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE').split(',')

config = APIConfig()

# Enhanced Pydantic models with validation
class UserQuery(BaseModel):
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="User's health-related question or request"
    )
    session_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Unique session identifier"
    )
    user_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional user metadata"
    )
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        # Basic sanitization
        return v.strip()
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not v.strip():
            raise ValueError('Session ID cannot be empty')
        # Remove any potentially harmful characters
        return ''.join(c for c in v if c.isalnum() or c in '-_')

class AgentResponse(BaseModel):
    response: str = Field(..., description="Agent's response to the user query")
    session_id: str = Field(..., description="Session identifier")
    response_type: str = Field(..., description="Type of response (health_advice, booking, error)")
    confidence_level: Optional[str] = Field(None, description="Confidence level of the response")
    processing_time: Optional[float] = Field(None, description="Time taken to process the request")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    active_sessions: int
    system_health: Dict[str, str]

class SessionManager:
    """Enhanced session management with cleanup and rate limiting"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timestamps: Dict[str, datetime] = {}
        self.rate_limits: Dict[str, list] = {}
        self.startup_time = datetime.now()
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data with automatic cleanup"""
        self._cleanup_expired_sessions()
        return self.sessions.get(session_id, {"status": "new"})
    
    def set_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Set session data with timestamp tracking"""
        self.sessions[session_id] = data
        self.session_timestamps[session_id] = datetime.now()
        
        # Limit number of sessions to prevent memory issues
        if len(self.sessions) > config.max_sessions:
            oldest_session = min(self.session_timestamps, key=self.session_timestamps.get)
            self.remove_session(oldest_session)
    
    def remove_session(self, session_id: str) -> None:
        """Remove session and its timestamp"""
        self.sessions.pop(session_id, None)
        self.session_timestamps.pop(session_id, None)
        self.rate_limits.pop(session_id, None)
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, timestamp in self.session_timestamps.items():
            if current_time - timestamp > timedelta(hours=config.max_session_age):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")
    
    def check_rate_limit(self, session_id: str) -> bool:
        """Check if session is within rate limits"""
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=config.rate_limit_window)
        
        if session_id not in self.rate_limits:
            self.rate_limits[session_id] = []
        
        # Remove old requests outside the window
        self.rate_limits[session_id] = [
            req_time for req_time in self.rate_limits[session_id]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.rate_limits[session_id]) >= config.rate_limit_requests:
            return False
        
        # Add current request
        self.rate_limits[session_id].append(current_time)
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        current_time = datetime.now()
        uptime = (current_time - self.startup_time).total_seconds()
        
        return {
            "active_sessions": len(self.sessions),
            "uptime_seconds": uptime,
            "total_rate_limited_sessions": len(self.rate_limits),
            "startup_time": self.startup_time.isoformat()
        }

# Initialize session manager
session_manager = SessionManager()

# Background task for periodic cleanup
async def cleanup_sessions():
    """Periodic session cleanup task"""
    while True:
        try:
            initial_count = len(session_manager.sessions)
            session_manager._cleanup_expired_sessions()
            final_count = len(session_manager.sessions)
            
            if initial_count != final_count:
                logger.info(f"Session cleanup: {initial_count - final_count} sessions removed")
            
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting AI Health Agent API...")
    
    # Start background tasks
    cleanup_task = asyncio.create_task(cleanup_sessions())
    
    try:
        yield
    finally:
        logger.info("Shutting down HealBot AI API...")
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

# Create FastAPI app with enhanced configuration
app = FastAPI(
    title="HealBot AI API",
    description="Advanced AI-powered health advisory, emergency triage and appointment booking system",
    version="2.0.0",
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=config.cors_methods,
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Emergency Mode Endpoints
@app.post("/emergency/toggle", tags=["Admin"])
async def toggle_emergency_mode():
    """Toggles the system-wide emergency mode ON or OFF."""
    global EMERGENCY_MODE_ACTIVE
    EMERGENCY_MODE_ACTIVE = not EMERGENCY_MODE_ACTIVE
    status = "ACTIVE" if EMERGENCY_MODE_ACTIVE else "INACTIVE"
    logger.warning(f"Emergency mode has been set to {status}")
    return {"message": f"Emergency mode is now {status}."}

@app.get("/status", tags=["Public"])
async def get_system_status():
    """Returns the current status of the system, including emergency mode."""
    return {"emergency_mode_active": EMERGENCY_MODE_ACTIVE, "timestamp": datetime.now().isoformat()}

@app.get("/alerts/current", tags=["Emergency"])
async def get_current_alerts():
    """Get currently active emergency alerts"""
    try:
        if not EMERGENCY_SYSTEM_AVAILABLE:
            return {"alerts": [], "message": "Emergency system not available"}
        
        # Use the emergency_system directly instead of importing tools
        active_alerts_raw = emergency_system.get_current_alerts()
        
        formatted_alerts = []
        for alert in active_alerts_raw:
            try:
                formatted_alerts.append({
                    "formatted_text": alert if isinstance(alert, str) else format_alert_for_display(alert),
                    "raw_data": alert,
                    "alert_type": alert.get('alert_type') if isinstance(alert, dict) else 'unknown',
                    "alert_level": alert.get('alert_level') if isinstance(alert, dict) else 'unknown',
                    "title": alert.get('title') if isinstance(alert, dict) else 'Emergency Alert',
                    "summary": alert.get('summary') if isinstance(alert, dict) else 'Alert active'
                })
            except Exception as e:
                logger.error(f"Error formatting alert: {e}")
                formatted_alerts.append({
                    "formatted_text": "Emergency alert active - formatting error",
                    "raw_data": alert,
                    "alert_type": "system_error",
                    "alert_level": "unknown"
                })
        
        return {
            "alerts": formatted_alerts,
            "count": len(formatted_alerts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting current alerts: {e}")
        return {
            "error": True,
            "status_code": 500,
            "message": "Unable to retrieve alerts",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/simulation/run/{simulation_type}", tags=["Emergency"])
async def run_emergency_simulation(simulation_type: str):
    """Run emergency simulations (outbreak or disaster)"""
    try:
        if not EMERGENCY_SYSTEM_AVAILABLE:
            raise HTTPException(status_code=503, detail="Emergency system not available")
        
        if simulation_type not in ["outbreak", "disaster"]:
            raise HTTPException(status_code=400, detail="Invalid simulation type. Use 'outbreak' or 'disaster'")
        
        logger.info(f"Running {simulation_type} simulation...")
        results = emergency_system.run_simulation(simulation_type)
        
        # Check for generated alerts
        alerts_generated = [r for r in results if r.get('generated_alert')]
        
        response_data = {
            "simulation_type": simulation_type,
            "reports_processed": len(results),
            "alerts_generated": len(alerts_generated),
            "timestamp": datetime.now().isoformat(),
            "results_summary": []
        }
        
        # Add alert details if any were generated
        if alerts_generated:
            alert = alerts_generated[0]['generated_alert']
            response_data["alert_triggered"] = {
                "title": alert['title'],
                "level": alert['alert_level'],
                "summary": alert['summary'],
                "formatted_display": format_alert_for_display(alert)
            }
        
        # Add summary of each report
        for i, result in enumerate(results, 1):
            response_data["results_summary"].append({
                "report_number": i,
                "emergency_type": result.get('emergency_type'),
                "vulnerability_level": result.get('vulnerability_level'),
                "alert_generated": result.get('generated_alert') is not None
            })
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@app.post("/emergency/process", tags=["Emergency"])
async def process_emergency_report(user_query: UserQuery):
    """Process individual emergency report (can trigger alerts)"""
    try:
        if not EMERGENCY_SYSTEM_AVAILABLE:
            raise HTTPException(status_code=503, detail="Emergency system not available")
        
        logger.info(f"Processing emergency report: {user_query.query[:100]}...")
        
        result = emergency_system.process_emergency_report(user_query.query)
        
        response_data = {
            "emergency_response": result['emergency_response'],
            "report_id": result.get('report_id'),
            "emergency_type": result.get('emergency_type'),
            "vulnerability_level": result.get('vulnerability_level'),
            "status": result.get('status', 'processed'),
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if this report generated a public alert
        if result.get('generated_alert'):
            alert = result['generated_alert']
            response_data["public_alert_generated"] = {
                "title": alert['title'],
                "level": alert['alert_level'],
                "summary": alert['summary'],
                "formatted_display": format_alert_for_display(alert)
            }
            logger.info(f"PUBLIC ALERT GENERATED: {alert['title']}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emergency processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency processing failed: {str(e)}")

@app.get("/simulation/status", tags=["Emergency"])
async def get_simulation_status():
    """Get current simulation system status"""
    if not EMERGENCY_SYSTEM_AVAILABLE:
        return {"available": False, "message": "Emergency system not available"}
    
    try:
        # Get some basic stats from the emergency system
        from agents.emergency_agent import EMERGENCY_REPORTS_DB, EPIDEMIC_TRACKING_DB
        
        return {
            "available": True,
            "total_emergency_reports": len(EMERGENCY_REPORTS_DB),
            "total_epidemic_reports": len(EPIDEMIC_TRACKING_DB),
            "current_alerts": len(emergency_system.get_current_alerts()) if emergency_system else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting simulation status: {e}")
        return {"available": True, "error": str(e)}

@app.post("/simulation/reset", tags=["Emergency"])
async def reset_simulation_data():
    """Reset simulation databases (for testing)"""
    try:
        if not EMERGENCY_SYSTEM_AVAILABLE:
            raise HTTPException(status_code=503, detail="Emergency system not available")
        
        # Access the database instance directly
        from agents.emergency_agent import EMERGENCY_REPORTS_DB, EPIDEMIC_TRACKING_DB
        
        # Clear the databases
        EMERGENCY_REPORTS_DB.clear()
        EPIDEMIC_TRACKING_DB.clear()
        
        # Clear active alerts through emergency system
        try:
            # Try to access the alert simulator directly
            from agents.emergency_agent import alert_simulator
            alert_simulator.last_alert_times.clear()
        except Exception as e:
            logger.warning(f"Could not clear alert simulator state: {e}")
        
        logger.info("All simulation data reset including alerts")
        
        return {
            "message": "All simulation data reset successfully including alerts",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting simulation data: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

# Rate limiting dependency
async def rate_limit_check(request: Request, user_query: UserQuery):
    """Check rate limits for requests"""
    session_id = user_query.session_id
    client_ip = request.client.host
    
    if not session_manager.check_rate_limit(f"{session_id}:{client_ip}"):
        logger.warning(f"Rate limit exceeded for session {session_id} from {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please wait before trying again.",
                "retry_after": config.rate_limit_window * 60
            }
        )
    
    return user_query

def classify_intent(query: str) -> str:
    """
    Uses an LLM to classify the user's intent with high accuracy.
    """
    # Initialize the LLM specifically for this routing task
    # Using a cheaper, faster model is ideal for classification
    router_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    prompt = ChatPromptTemplate.from_template(
        """You are an expert at classifying user intent for a health AI agent. 
        Analyze the user's query and categorize it into one of the following intents: 
        'health_query', 'booking_request', or 'emergency'.

        - 'health_query': The user is asking for general information, definitions, causes, symptoms of a disease in a non-personal context, prevention methods, or health tips.
          Examples: "What are the symptoms of typhoid?", "How to prevent malaria?", "Tell me about nutrition."

        - 'booking_request': The user is describing their own personal symptoms, asking to see a doctor, or scheduling an appointment.
          Examples: "I have a fever and a headache.", "I need to book an appointment.", "My stomach hurts."

        - 'emergency': The user describes a life-threatening situation like severe chest pain, difficulty breathing, heavy bleeding, or loss of consciousness.
          Examples: "I can't breathe!", "He is unconscious!", "Severe chest pain."

        Respond with ONLY the category name and nothing else.

        User Query: "{user_query}"
        """
    )
    
    # Create the classification chain
    chain = prompt | router_llm | StrOutputParser()
    
    # Invoke the chain to get the intent
    intent = chain.invoke({"user_query": query})
    
    # Clean up the response to ensure it's just the keyword
    return intent.strip().lower()

async def process_health_query(query: str, session_id: str) -> Dict[str, Any]:
    """Process health advisory queries with enhanced error handling"""
    try:
        logger.info(f"Processing health query for session {session_id}")
        start_time = datetime.now()
        
        state = health_adviser_app.invoke({"question": query})
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "response": state.get('answer', 'Unable to generate response'),
            "response_type": "health_advice",
            "confidence_level": state.get('confidence_level'),
            "processing_time": processing_time,
            "metadata": {
                "documents_retrieved": len(state.get('documents', [])),
                "retrieval_score": state.get('retrieval_score', 0.0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing health query: {e}\n{traceback.format_exc()}")
        return {
            "response": "I apologize, but I'm unable to process your health question right now. Please try again later or consult a healthcare professional.",
            "response_type": "error",
            "confidence_level": "Very Low",
            "metadata": {"error": str(e)}
        }

async def process_booking_request(query: str, session_id: str, session_state: Dict[str, Any]) -> Dict[str, Any]:
    """Process booking requests with improved continuation handling"""
    try:
        logger.info(f"Processing booking request for session {session_id}")
        start_time = datetime.now()

        ql = query.lower().strip()

        # If we are continuing an existing booking flow:
        if session_state.get("status") == "awaiting_confirmation":
            logger.info(f"Continuing existing booking flow for session {session_id}")
            
            # Check if we've been stuck in confirmation loop
            confirmation_count = session_state.get("confirmation_attempts", 0)
            if confirmation_count >= 2:
                logger.warning(f"Session {session_id} stuck in confirmation loop, forcing completion")
                # Force completion to avoid infinite loop
                session_manager.set_session(session_id, {"status": "completed"})
                return {
                    "response": "I see you'd like to proceed with booking. Your appointment request has been noted and our team will contact you shortly to finalize the scheduling.",
                    "response_type": "booking_confirmation",
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "metadata": {"booking_completed": True, "loop_prevented": True}
                }
            
            # Increment confirmation attempts
            session_state["confirmation_attempts"] = confirmation_count + 1
            session_manager.set_session(session_id, session_state)
            
            # Enhanced confirmation detection
            confirmation_patterns = [
                # Direct confirmations
                "yes", "yep", "yeah", "sure", "ok", "okay", "confirm",
                "please book", "book it", "schedule it", "go ahead",
                "find an appointment", "book appointment", "yes find",
                "proceed", "continue", "that's fine", "sounds good",
                # Scheduling responses
                "tomorrow", "today", "next week", "morning", "evening",
                "afternoon", "am", "pm", "monday", "tuesday", "wednesday",
                "thursday", "friday", "saturday", "sunday"
            ]
            
            # Check for confirmation or scheduling details
            is_confirmation = any(pattern in ql for pattern in confirmation_patterns)
            
            # Check if it's a date/time specification
            has_datetime_info = any(indicator in ql for indicator in [
                "am", "pm", "morning", "evening", "afternoon", "tomorrow", 
                "today", "next", "monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday", ":", "/"
            ])
            
            # Check if it's additional symptom information
            symptom_words = [
                "pain", "hurt", "ache", "feel", "symptom", "problem",
                "worse", "better", "since", "started", "days", "weeks"
            ]
            has_symptom_info = any(word in ql for word in symptom_words)
            
            if is_confirmation or has_datetime_info or (has_symptom_info and len(ql.split()) > 3):
                logger.info(f"User provided booking continuation: confirmation={is_confirmation}, datetime={has_datetime_info}, symptom_info={has_symptom_info}")
                logger.info(f"User query for continuation: '{query}'")
                
                # Get saved booking data
                saved_data = session_state.get("data", {})
                
                # Add the follow-up response
                saved_data.setdefault("follow_up_responses", []).append(query)
                saved_data["confirmation_received"] = True
                saved_data["user_confirmed"] = True
                
                # Process the booking continuation using the actual booking agent
                try:
                    logger.info(f"Invoking booking agent continuation with data keys: {list(saved_data.keys())}")
                    
                    # The booking agent expects a BookingState, so we need to convert saved_data
                    continuation_state = {
                        "user_query": saved_data.get("user_query", query),
                        "symptoms": saved_data.get("symptoms", []),
                        "urgency": saved_data.get("urgency", "Low"),
                        "specialty": saved_data.get("specialty", "General Physician"),
                        "potential_diseases": saved_data.get("potential_diseases", []),
                        "available_slots": saved_data.get("available_slots", []),
                        "final_response": saved_data.get("final_response", ""),
                        "error_message": saved_data.get("error_message"),
                        "retry_count": saved_data.get("retry_count", 0),
                        "processing_timestamp": datetime.now().isoformat(),
                        "follow_up_responses": saved_data.get("follow_up_responses", [])
                    }
                    
                    # Use the booking agent's continue_booking node directly
                    from agents.booking_agent import find_slots_node, book_appointment_node, decide_after_finding_slots
                    
                    # First find available slots
                    continuation_state = find_slots_node(continuation_state)
                    logger.info(f"Found {len(continuation_state.get('available_slots', []))} slots")
                    
                    # Then decide what to do next
                    next_step = decide_after_finding_slots(continuation_state)
                    logger.info(f"Next step after finding slots: {next_step}")
                    
                    if next_step == "book_slot":
                        # Book the appointment
                        continuation_state = book_appointment_node(continuation_state)
                    elif next_step == "no_slots":
                        # Handle no slots available
                        from agents.booking_agent import no_slots_found_node
                        continuation_state = no_slots_found_node(continuation_state)
                    else:
                        # Handle errors
                        from agents.booking_agent import error_handler_node
                        continuation_state = error_handler_node(continuation_state)
                    
                    # Mark session as completed
                    session_manager.set_session(session_id, {"status": "completed"})
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    return {
                        "response": continuation_state.get('final_response', 'Booking process completed'),
                        "response_type": "booking_confirmation",
                        "processing_time": processing_time,
                        "metadata": {
                            "booking_completed": True,
                            "slots_found": len(continuation_state.get('available_slots', [])),
                            "next_step": next_step
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Error in booking agent continuation: {e}\n{traceback.format_exc()}")
                    
                    # Fallback to manual booking confirmation using saved data
                    session_manager.set_session(session_id, {"status": "completed"})
                    
                    symptoms = saved_data.get('symptoms', ['As discussed'])
                    urgency = saved_data.get('urgency', 'Low')
                    specialty = saved_data.get('specialty', 'General Physician')
                    
                    fallback_response = f"""Appointment Request Confirmed

**Pre-Consultation Summary:**
• **Symptoms:** {', '.join(symptoms)}
• **Urgency Level:** {urgency}
• **Recommended Specialty:** {specialty}

**Next Steps:**
• Your appointment request has been submitted to our booking system
• Our team will contact you within 2-4 hours to confirm availability
• Please keep your phone available for the confirmation call
• Bring any relevant medical records to your appointment

**Hospital Information:**
• We will help you find the best available appointment
• Multiple hospitals and specialists are available
• Emergency services: Call 108 if your condition worsens

Thank you for using our healthcare booking service. We'll be in touch soon!"""
                    
                    return {
                        "response": fallback_response,
                        "response_type": "booking_confirmation",
                        "processing_time": (datetime.now() - start_time).total_seconds(),
                        "metadata": {"booking_completed": True, "fallback_used": True}
                    }
            else:
                # Ask for explicit confirmation
                processing_time = (datetime.now() - start_time).total_seconds()
                return {
                    "response": "I have your appointment request ready. Would you like me to proceed with booking? Please confirm with 'Yes' or provide your preferred date and time.",
                    "response_type": "booking_inquiry",
                    "processing_time": processing_time,
                    "metadata": {"awaiting_explicit_confirmation": True}
                }

        # Handle new booking request
        logger.info(f"Processing new booking request for session {session_id}: {query[:100]}...")
        
        initial_state: BookingState = {"user_query": query}
        
        try:
            report_state = booking_agent_app.invoke(initial_state)
            
            # Save state for potential continuation
            session_manager.set_session(session_id, {
                "status": "awaiting_confirmation",
                "data": report_state,
                "created_at": datetime.now().isoformat(),
                "original_query": query
            })

            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "response": report_state.get('final_response', 'Unable to process booking request'),
                "response_type": "booking_inquiry",
                "processing_time": processing_time,
                "metadata": {
                    "symptoms_found": len(report_state.get('symptoms', [])),
                    "urgency": report_state.get('urgency'),
                    "specialty": report_state.get('specialty'),
                    "awaiting_confirmation": True,
                    "booking_flow_started": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error invoking booking agent: {e}")
            return {
                "response": "I understand you're looking to book an appointment. Could you please provide more details about your symptoms or the type of consultation you need?",
                "response_type": "booking_inquiry",
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {"error": "booking_agent_error", "fallback_used": True}
            }

    except Exception as e:
        logger.error(f"Error processing booking request: {e}\n{traceback.format_exc()}")
        return {
            "response": "I apologize, but I'm unable to process your booking request right now. Please try again later or contact the hospital directly.",
            "response_type": "error",
            "metadata": {"error": str(e)}
        }

@app.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    user_query: UserQuery = Depends(rate_limit_check),
    request: Request = None
) -> AgentResponse:
    """Enhanced chat endpoint with emergency alert integration."""
    
    start_time = datetime.now()
    session_id = user_query.session_id
    query = user_query.query
    
    logger.info(f"Chat request from session {session_id}: {query[:100]}...")
    
    # Check for active alerts and include them in response
    active_alerts = []
    alert_display_text = ""
    
    if EMERGENCY_SYSTEM_AVAILABLE:
        try:
            active_alerts = emergency_system.get_current_alerts()
            if active_alerts:
                alert_texts = [format_alert_for_display(alert) for alert in active_alerts]
                alert_display_text = "\n\n" + "\n\n".join(alert_texts) + "\n\n--- End of Alerts ---\n\n"
                logger.info(f"Including {len(active_alerts)} active alerts in response")
        except Exception as e:
            logger.error(f"Error checking for alerts: {e}")
    
    # PRIORITY 1: Check for Emergency Mode
    if EMERGENCY_MODE_ACTIVE:
        logger.warning(f"EMERGENCY MODE ACTIVE - Routing to emergency agent for session {session_id}")
        try:
            # Process as emergency but also check if it generates new alerts
            if EMERGENCY_SYSTEM_AVAILABLE:
                emergency_result = emergency_system.process_emergency_report(query)
                emergency_response = emergency_result['emergency_response']
                
                # If this emergency report generated a NEW alert, include it
                if emergency_result.get('generated_alert'):
                    new_alert = emergency_result['generated_alert']
                    new_alert_text = format_alert_for_display(new_alert)
                    emergency_response = f"{new_alert_text}\n\n--- New Alert Generated ---\n\n{emergency_response}"
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return AgentResponse(
                    response=alert_display_text + emergency_response,
                    session_id=session_id,
                    response_type="emergency_response",
                    processing_time=processing_time,
                    metadata={
                        "emergency_mode": True,
                        "active_alerts_count": len(active_alerts),
                        "new_alert_generated": emergency_result.get('generated_alert') is not None
                    }
                )
            else:
                # Fallback if emergency system not available
                return AgentResponse(
                    response=alert_display_text + "Emergency mode is active. Please state your emergency clearly. If you have a medical emergency, call 108 immediately.",
                    session_id=session_id,
                    response_type="emergency_response",
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    metadata={"emergency_mode": True, "system_fallback": True}
                )
                
        except Exception as e:
            logger.error(f"Critical error in emergency mode: {e}")
            return AgentResponse(
                response="System error in emergency mode. Please call 108 for immediate medical assistance.",
                session_id=session_id,
                response_type="system_error",
                processing_time=(datetime.now() - start_time).total_seconds(),
                metadata={"error": "Emergency mode failure"}
            )

    # Standard Logic (if emergency mode is OFF)
    try:
        session_state = session_manager.get_session(session_id)
        
        # Check if this might be an emergency report that could trigger alerts
        emergency_keywords = ['emergency', 'urgent', 'critical', 'chest pain', 'breathing', 'fever', 'outbreak', 'flooding', 'disaster']
        might_be_emergency = any(keyword in query.lower() for keyword in emergency_keywords)
        
        if might_be_emergency and EMERGENCY_SYSTEM_AVAILABLE:
            try:
                # Process through emergency system to check for alert generation
                emergency_result = emergency_system.process_emergency_report(query)
                
                # If this generated a new public alert, we need to handle it specially
                if emergency_result.get('generated_alert'):
                    new_alert = emergency_result['generated_alert']
                    new_alert_text = format_alert_for_display(new_alert)
                    
                    # Return the emergency response with the new alert
                    full_response = f"{new_alert_text}\n\n--- New Alert Generated ---\n\n{alert_display_text}{emergency_result['emergency_response']}"
                    
                    return AgentResponse(
                        response=full_response,
                        session_id=session_id,
                        response_type="emergency_with_alert",
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        metadata={
                            "new_alert_generated": True,
                            "alert_type": new_alert.get('alert_type'),
                            "alert_level": new_alert.get('alert_level'),
                            "active_alerts_count": len(active_alerts)
                        }
                    )
                
                # If emergency system processed it but no alert, check if it's critical individual emergency
                if emergency_result.get('vulnerability_level') in ['critical', 'high']:
                    return AgentResponse(
                        response=alert_display_text + emergency_result['emergency_response'],
                        session_id=session_id,
                        response_type="emergency_individual",
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        metadata={
                            "emergency_type": emergency_result.get('emergency_type'),
                            "vulnerability_level": emergency_result.get('vulnerability_level'),
                            "active_alerts_count": len(active_alerts)
                        }
                    )
            except Exception as e:
                logger.error(f"Error processing potential emergency: {e}")
                # Continue with normal processing
        
        # Continue with normal intent classification and processing
        is_booking_continuation = session_state.get("status") == "awaiting_confirmation" and "yes" in query.lower()

        if is_booking_continuation:
            intent = 'booking_request'
        else:
            intent = classify_intent(query)
            
        logger.info(f"Classified intent: {intent} for session {session_id}")
        
        if intent == 'emergency':
            response_data = {
                "response": "🚨 **EMERGENCY DETECTED** 🚨\n\nThis may be a medical emergency. Please **call 108** or go to the nearest emergency room immediately.",
                "response_type": "emergency_alert",
            }
        elif intent == 'health_query':
            response_data = await process_health_query(query, session_id)
        elif intent == 'booking_request':
            response_data = await process_booking_request(query, session_id, session_state)
        else: # Fallback
            response_data = await process_health_query(query, session_id)
        
        # Add alerts to the beginning of the response
        final_response = alert_display_text + response_data["response"]
        
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        return AgentResponse(
            response=final_response,
            session_id=session_id,
            response_type=response_data.get("response_type", "unknown"),
            processing_time=total_processing_time,
            metadata={
                **response_data.get("metadata", {}),
                "active_alerts_count": len(active_alerts),
                "alerts_included": len(active_alerts) > 0
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}\n{traceback.format_exc()}")
        error_response = alert_display_text + "An unexpected server error occurred."
        return JSONResponse(
            status_code=500,
            content={
                "response": error_response,
                "session_id": session_id,
                "response_type": "system_error",
            }
        )

@app.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Comprehensive health check endpoint"""
    try:
        current_time = datetime.now()
        stats = session_manager.get_stats()
        
        # Test basic functionality
        system_health = {}
        
        # Test health adviser
        try:
            test_result = health_adviser_app.invoke({"question": "test"})
            system_health["health_adviser"] = "healthy"
        except Exception as e:
            logger.error(f"Health adviser test failed: {e}")
            system_health["health_adviser"] = "unhealthy"
        
        # Test booking agent
        try:
            test_state: BookingState = {"user_query": "test headache"}
            booking_agent_app.invoke(test_state)
            system_health["booking_agent"] = "healthy"
        except Exception as e:
            logger.error(f"Booking agent test failed: {e}")
            system_health["booking_agent"] = "unhealthy"
        
        # Overall system status
        overall_status = "healthy" if all(
            status == "healthy" for status in system_health.values()
        ) else "degraded"
        
        return HealthStatus(
            status=overall_status,
            timestamp=current_time.isoformat(),
            version="2.0.0",
            uptime_seconds=stats["uptime_seconds"],
            active_sessions=stats["active_sessions"],
            system_health=system_health
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version="2.0.0",
            uptime_seconds=0,
            active_sessions=0,
            system_health={"error": str(e)}
        )

@app.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get session status and metadata"""
    try:
        session_data = session_manager.get_session(session_id)
        session_timestamp = session_manager.session_timestamps.get(session_id)
        
        return {
            "session_id": session_id,
            "status": session_data.get("status", "new"),
            "created_at": session_timestamp.isoformat() if session_timestamp else None,
            "last_activity": session_timestamp.isoformat() if session_timestamp else None,
            "awaiting_confirmation": session_data.get("status") == "awaiting_confirmation",
            "metadata": {
                "has_data": "data" in session_data,
                "data_keys": list(session_data.get("data", {}).keys()) if "data" in session_data else []
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve session status")

@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str) -> Dict[str, str]:
    """Clear a specific session"""
    try:
        session_manager.remove_session(session_id)
        logger.info(f"Session {session_id} cleared successfully")
        return {"message": f"Session {session_id} cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail="Unable to clear session")

@app.post("/sessions/cleanup")
async def manual_cleanup(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Trigger manual session cleanup"""
    try:
        background_tasks.add_task(session_manager._cleanup_expired_sessions)
        return {"message": "Session cleanup initiated"}
        
    except Exception as e:
        logger.error(f"Error initiating cleanup: {e}")
        raise HTTPException(status_code=500, detail="Unable to initiate cleanup")

@app.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get API statistics"""
    try:
        stats = session_manager.get_stats()
        
        return {
            "api_version": "2.0.0",
            "configuration": {
                "max_sessions": config.max_sessions,
                "max_session_age_hours": config.max_session_age,
                "rate_limit_requests": config.rate_limit_requests,
                "rate_limit_window_minutes": config.rate_limit_window
            },
            "runtime_stats": stats,
            "system_info": {
                "debug_mode": config.debug,
                "host": config.host,
                "port": config.port
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve statistics")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.warning(f"HTTP {exc.status_code} error for {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception for {request.url}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("="*50)
    logger.info("AI Health Agent API Starting Up")
    logger.info(f"Version: 2.0.0")
    logger.info(f"Host: {config.host}:{config.port}")
    logger.info(f"Debug Mode: {config.debug}")
    logger.info(f"Max Sessions: {config.max_sessions}")
    logger.info(f"Session Age Limit: {config.max_session_age} hours")
    logger.info(f"Rate Limit: {config.rate_limit_requests} requests per {config.rate_limit_window} minutes")
    logger.info(f"Emergency System Available: {EMERGENCY_SYSTEM_AVAILABLE}")
    if EMERGENCY_SYSTEM_AVAILABLE:
        try:
            current_alerts = emergency_system.get_current_alerts()
            logger.info(f"Active Emergency Alerts: {len(current_alerts)}")
        except Exception as e:
            logger.warning(f"Could not check alert status: {e}")
    logger.info("="*50)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("AI Health Agent API Shutting Down")
    logger.info(f"Final session count: {len(session_manager.sessions)}")

def run_api():
    """Run the API with proper configuration"""
    try:
        uvicorn.run(
            "main:app",
            host=config.host,
            port=config.port,
            reload=config.debug,
            log_level="info" if not config.debug else "debug",
            access_log=True,
            server_header=False,
            date_header=False
        )
    except KeyboardInterrupt:
        logger.info("API shutdown requested by user")
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise

if __name__ == "__main__":
    run_api()
# [2025-09-30] feat(emergency): configure emergency contact resolver and SOS routing

# [2025-10-05] fix(booking): resolve doctor slot collision edge case

# [2025-10-09] feat(agent): introduce multi-turn conversation memory buffers

# [2025-10-13] feat(emergency): add nearest hospital geo-lookup support

# [2025-10-18] test: add test suite for doctor booking agent edge cases

# [2025-10-22] feat(booking): support multiple hospital branch locations

# [2025-10-26] fix(db): ensure atomic transactions during appointment commits

# [2025-10-30] refactor(agent): improve parsing resilience for unstructured input

# [2025-11-04] feat(tools): add telemetry metrics for agent response latency

# [2025-11-08] feat(emergency): support paramedic voice dispatch integration

# [2025-11-12] fix(tools): handle HTTP 429 rate limit with exponential backoff

# [2025-11-16] fix(agent): prevent premature conclusion in multi-symptom queries

# [2025-11-21] refactor(tools): abstract notification provider interface

# [2025-11-25] feat(emergency): broadcast SOS to designated family contacts

# [2025-11-29] fix(api): validate UUID format for incoming session identifiers

# [2025-12-03] docs: revise project README with HealBot AI branding and features

# [2025-12-08] docs: update API documentation and endpoint descriptions

# [2025-12-12] feat(dashboard): add live server status indicator badge

# [2025-12-16] feat(agent): add pregnancy & maternal health safety guidance

# [2025-12-21] fix(dashboard): fix chart rendering glitch on empty alert data

# [2025-12-25] test: add stress tests for high-volume emergency simulation
