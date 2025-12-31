import uuid
import logging
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import traceback
import random
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

# Import tools with fixed import structure
# At the top of the file, add:
try:
    from tools.emergency_tools import store_alert
except ImportError:
    def store_alert(alert):
        logger.warning("store_alert function not available")
try:
    from tools.emergency_tools import (
        save_emergency_report, 
        alert_emergency_services,
        calculate_epidemic_metrics,
        get_resource_availability,
        track_migration_patterns,
        get_population_density_data,
        EMERGENCY_REPORTS_DB,
        EPIDEMIC_TRACKING_DB
    )
    
    # Try to import other agents - use mock if not available
    try:
        from booking_agent import booking_agent_app
    except ImportError:
        def booking_agent_app(state):
            return {"final_response": "Appointment booking would be handled here"}
            
except ImportError as e:
    logging.warning(f"Import issues: {e}")
    # Create mock functions
    def save_emergency_report(data): return "Report saved"
    def alert_emergency_services(data): return "Services alerted"
    EMERGENCY_REPORTS_DB = []
    EPIDEMIC_TRACKING_DB = []

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmergencyType(Enum):
    DISEASE_OUTBREAK = "disease_outbreak"
    NATURAL_DISASTER = "natural_disaster"
    MEDICAL_EMERGENCY = "medical_emergency"
    
class VulnerabilityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AlertType(Enum):
    EPIDEMIC_WARNING = "epidemic_warning"
    DISASTER_ALERT = "disaster_alert"
    SYSTEM_NOTIFICATION = "system_notification"

class EmergencyState(TypedDict):
    user_query: str
    report_id: str
    emergency_type: str
    location: Dict[str, float]
    vulnerability_level: str
    symptoms: List[str]
    demographics: Dict[str, Any]
    contact_info: Dict[str, str]
    final_response: str
    analytics_data: Dict[str, Any]
    requires_booking: bool
    error_message: Optional[str]
    generated_alert: Optional[Dict[str, Any]]  # New field for alerts

class EmergencyClassification(BaseModel):
    emergency_type: str = Field(description="Type: disease_outbreak, natural_disaster, or medical_emergency")
    vulnerability_level: str = Field(description="Level: critical, high, medium, or low")
    symptoms: List[str] = Field(description="List of reported symptoms")
    extracted_details: str = Field(description="Summary of the emergency situation")
    requires_immediate_response: bool = Field(description="True if emergency services needed immediately")
    suspected_condition: str = Field(description="Suspected medical condition or disaster type")

class AlertSimulator:
    """Manages alert generation based on accumulated reports"""
    
    def __init__(self):
        self.alert_thresholds = {
            'disease_outbreak': {
                'similar_symptoms_count': 2,  # Changed from 3 to 2
                'time_window_hours': 24,
                'geographic_radius_km': 10
            },
            'natural_disaster': {
                'similar_reports_count': 2,
                'time_window_hours': 6,
                'geographic_radius_km': 20
            }
        }
        
        self.last_alert_times = {}  # Prevent spam alerts
        self.alert_cooldown_hours = 6
        
    def should_generate_alert(self, emergency_type: str, current_report: Dict) -> bool:
        """Check if conditions are met to generate a public alert"""
        try:
            if emergency_type not in self.alert_thresholds:
                return False
            
            # Check cooldown period
            last_alert_key = f"{emergency_type}_{current_report.get('location', {}).get('district', 'unknown')}"
            if last_alert_key in self.last_alert_times:
                hours_since_last = (datetime.now() - self.last_alert_times[last_alert_key]).total_seconds() / 3600
                if hours_since_last < self.alert_cooldown_hours:
                    logger.info(f"Alert cooldown active for {last_alert_key}: {hours_since_last:.1f}h < {self.alert_cooldown_hours}h")
                    return False
            
            thresholds = self.alert_thresholds[emergency_type]
            
            # Get recent similar reports
            recent_reports = self._get_recent_similar_reports(
                emergency_type, 
                current_report, 
                thresholds['time_window_hours']
            )
            
            # Debug logging
            logger.info(f"Alert check for {emergency_type}: found {len(recent_reports)} similar reports, need {thresholds['similar_symptoms_count']}")
            
            # Check if threshold is met
            should_alert = len(recent_reports) >= thresholds['similar_symptoms_count']
            
            if should_alert:
                self.last_alert_times[last_alert_key] = datetime.now()
                logger.info(f"🚨 ALERT THRESHOLD MET for {emergency_type}: {len(recent_reports)} reports >= {thresholds['similar_symptoms_count']}")
            else:
                logger.info(f"Alert threshold not met: {len(recent_reports)} < {thresholds['similar_symptoms_count']}")
            
            return should_alert
            
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
            return False
    
    def _get_recent_similar_reports(self, emergency_type: str, current_report: Dict, hours: int) -> List[Dict]:
        """Get recent reports similar to current one"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        current_symptoms = set(current_report.get('symptoms', []))

        # Fix location comparison
        current_location = current_report.get('location', {})
        if isinstance(current_location, dict):
            current_district = current_location.get('district', 'warangal')
        else:
            current_district = str(current_location)

        similar_reports = []

        # Search in appropriate database
        search_db = EPIDEMIC_TRACKING_DB if emergency_type == 'disease_outbreak' else EMERGENCY_REPORTS_DB

        logger.info(f"Searching {len(search_db)} reports in {emergency_type} database for similar reports")
        logger.info(f"Current district: '{current_district}', Current symptoms: {list(current_symptoms)}")

        for report in search_db:
            try:
                # Fix timestamp parsing - handle both 'timestamp' and 'created_at'
                report_time_str = report.get('timestamp') or report.get('created_at', '')
                if not report_time_str:
                    continue

                report_time = datetime.fromisoformat(report_time_str)
                if report_time < cutoff_time:
                    logger.debug(f"Report {report.get('report_id', 'unknown')} too old: {report_time}")
                    continue

                # Fix location similarity check
                report_location = report.get('location', {})
                if isinstance(report_location, dict):
                    report_district = report_location.get('district', 'warangal')
                else:
                    report_district = str(report_location)

                # More flexible location matching
                if report_district.lower() != current_district.lower():
                    logger.debug(f"Location mismatch: '{report_district}' vs '{current_district}'")
                    continue

                # Check symptom/condition similarity
                if emergency_type == 'disease_outbreak':
                    report_symptoms = set(report.get('symptoms', []))
                    logger.debug(f"Comparing symptoms: current={list(current_symptoms)} vs report={list(report_symptoms)}")

                    if len(current_symptoms) == 0 and len(report_symptoms) == 0:
                        similarity = 1.0  # Both have no symptoms specified
                    elif len(current_symptoms) == 0 or len(report_symptoms) == 0:
                        similarity = 0.0  # One has symptoms, other doesn't
                    else:
                        intersection = len(current_symptoms.intersection(report_symptoms))
                        union = len(current_symptoms.union(report_symptoms))
                        similarity = intersection / max(union, 1)

                    logger.debug(f"Symptom similarity: {similarity}")

                    if similarity >= 0.3:  # Lowered threshold from 0.5 to 0.3
                        similar_reports.append(report)
                        logger.info(f"Added similar report: {report.get('report_id', 'unknown')} (similarity: {similarity:.2f})")
                else:  # natural_disaster
                    if report.get('emergency_type') == emergency_type:
                        similar_reports.append(report)
                        logger.info(f"Added similar disaster report: {report.get('report_id', 'unknown')}")

            except Exception as e:
                logger.error(f"Error processing report {report.get('report_id', 'unknown')} for similarity: {e}")
                continue

        logger.info(f"Found {len(similar_reports)} similar reports for {emergency_type}")
        return similar_reports
    
    def generate_alert(self, emergency_type: str, reports: List[Dict], current_report: Dict) -> Dict[str, Any]:
        """Generate a public alert based on accumulated reports"""
        try:
            district = current_report.get('location', {}).get('district', 'Warangal')
            
            if emergency_type == 'disease_outbreak':
                return self._generate_epidemic_alert(reports, current_report, district)
            elif emergency_type == 'natural_disaster':
                return self._generate_disaster_alert(reports, current_report, district)
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error generating alert: {e}")
            return {}
    
    def _generate_epidemic_alert(self, reports: List[Dict], current_report: Dict, district: str) -> Dict[str, Any]:
        """Generate epidemic/outbreak alert"""
        # Analyze symptoms across reports
        all_symptoms = []
        for report in reports + [current_report]:
            all_symptoms.extend(report.get('symptoms', []))
        
        symptom_counts = {}
        for symptom in all_symptoms:
            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
        
        top_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Generate alert levels
        total_cases = len(reports) + 1
        alert_level = "HIGH" if total_cases >= 10 else "MODERATE" if total_cases >= 7 else "LOW"
        
        suspected_conditions = [r.get('suspected_condition', 'unknown') for r in reports if r.get('suspected_condition')]
        most_likely_condition = max(set(suspected_conditions), key=suspected_conditions.count) if suspected_conditions else "viral infection"
        
        return {
            'alert_type': 'epidemic_warning',
            'alert_level': alert_level,
            'title': f'Disease Outbreak Alert - {district}',
            'summary': f'{total_cases} cases with similar symptoms reported in {district} area',
            'details': {
                'total_cases': total_cases,
                'time_period': '24 hours',
                'affected_area': district,
                'primary_symptoms': [s[0] for s in top_symptoms],
                'suspected_condition': most_likely_condition,
                'growth_rate': f'{(total_cases-1)*100/max(len(reports), 1):.0f}% increase'
            },
            'recommendations': [
                'Avoid crowded areas if possible',
                'Maintain good hygiene practices',
                'Monitor your health closely',
                'Seek medical attention if symptoms develop',
                'Follow official health department guidelines'
            ],
            'emergency_contacts': {
                'health_department': '1075',
                'ambulance': '108',
                'district_collector': '+91-xxx-xxx-xxxx'
            },
            'timestamp': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=48)).isoformat()
        }
    
    def _generate_disaster_alert(self, reports: List[Dict], current_report: Dict, district: str) -> Dict[str, Any]:
        """Generate natural disaster alert"""
        total_reports = len(reports) + 1
        alert_level = "CRITICAL" if total_reports >= 5 else "HIGH" if total_reports >= 3 else "MODERATE"
        
        # Analyze disaster types
        disaster_types = [r.get('suspected_condition', 'infrastructure damage') for r in reports]
        primary_disaster = max(set(disaster_types), key=disaster_types.count) if disaster_types else "flooding"
        
        return {
            'alert_type': 'disaster_alert',
            'alert_level': alert_level,
            'title': f'Natural Disaster Alert - {district}',
            'summary': f'{total_reports} disaster-related reports in {district} area',
            'details': {
                'total_reports': total_reports,
                'time_period': '6 hours',
                'affected_area': district,
                'primary_disaster_type': primary_disaster,
                'severity_trend': 'increasing'
            },
            'immediate_actions': [
                'Move to higher ground if flooding',
                'Stay indoors unless evacuating',
                'Keep emergency supplies ready',
                'Monitor official disaster management updates',
                'Avoid damaged infrastructure'
            ],
            'evacuation_info': {
                'evacuation_centers': [
                    'Government School, Main Road',
                    'Community Center, Station Road',
                    'District Collector Office'
                ],
                'transportation': 'Emergency buses available from main intersections'
            },
            'emergency_contacts': {
                'disaster_management': '1070',
                'fire_department': '101',
                'police': '100',
                'rescue_operations': '108'
            },
            'timestamp': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }

# Initialize alert simulator
alert_simulator = AlertSimulator()

class EmergencyConfig:
    """Configuration for emergency system"""
    def __init__(self):
        self.model_name = "gpt-4o"
        self.temperature = 0
        self.warangal_coordinates = {"lat": 17.9689, "lon": 79.5894, "district": "warangal"}
        self.emergency_hotlines = {
            "ambulance": "108",
            "disaster_management": "1070",
            "police": "100",
            "fire": "101"
        }

config = EmergencyConfig()

# Initialize LLM with error handling
try:
    llm = ChatOpenAI(model=config.model_name, temperature=config.temperature)
    logger.info("Emergency LLM initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    # Mock LLM for testing
    class MockLLM:
        def with_structured_output(self, schema):
            def mock_chain(input_data):
                return EmergencyClassification(
                    emergency_type="disease_outbreak",
                    vulnerability_level="medium",
                    symptoms=["fever", "cough"],
                    extracted_details="Mock classification",
                    requires_immediate_response=False,
                    suspected_condition="viral infection"
                )
            return lambda x: mock_chain
    llm = MockLLM()

def initialize_emergency_state(state: EmergencyState) -> EmergencyState:
    """Initialize emergency state with default values"""
    defaults = {
        'report_id': str(uuid.uuid4()),
        'location': config.warangal_coordinates,
        'symptoms': [],
        'demographics': {},
        'contact_info': {},
        'analytics_data': {},
        'requires_booking': False,
        'error_message': None,
        'generated_alert': None
    }
    
    for key, value in defaults.items():
        if key not in state:
            state[key] = value
    
    return state

def collect_and_classify_node(state: EmergencyState) -> EmergencyState:
    """Enhanced classification with alert generation"""
    logger.info("Starting emergency data collection and classification")
    
    try:
        state = initialize_emergency_state(state)
        
        # Enhanced classification prompt
        classification_prompt = ChatPromptTemplate.from_template("""
        You are an emergency response classifier for Warangal, Telangana. Analyze the user's report and classify it comprehensively.

        EMERGENCY TYPES:
        - disease_outbreak: Symptoms suggesting infectious disease, fever clusters, unusual illness patterns
        - natural_disaster: Flooding, cyclone damage, building collapse, infrastructure failure
        - medical_emergency: Individual medical crisis, accidents, acute conditions

        VULNERABILITY LEVELS:
        - critical: Life-threatening, requires immediate emergency response
        - high: Serious condition needing urgent care within hours
        - medium: Concerning symptoms requiring monitoring/care within 24-48 hours
        - low: Mild symptoms, precautionary measures sufficient

        User Report: "{user_input}"
        Location: Warangal, Telangana

        Provide a JSON response with exact field names: emergency_type, vulnerability_level, symptoms, extracted_details, requires_immediate_response, suspected_condition
        """)

        try:
            # Try structured output first
            if hasattr(llm, 'with_structured_output'):
                structured_llm = llm.with_structured_output(EmergencyClassification)
                chain = classification_prompt | structured_llm
                classification = chain.invoke({"user_input": state['user_query']})
            else:
                # Fallback: use regular LLM with JSON parsing
                from langchain_core.output_parsers import JsonOutputParser
                parser = JsonOutputParser(pydantic_object=EmergencyClassification)
                chain = classification_prompt | llm | parser
                classification_dict = chain.invoke({"user_input": state['user_query']})
                # Convert dict to EmergencyClassification object
                classification = EmergencyClassification(**classification_dict)
        except Exception as llm_error:
            logger.error(f"LLM classification failed: {llm_error}")
            # Fallback classification based on keywords
            classification = create_fallback_classification(state['user_query'])

        # Ensure classification is the right type
        if not hasattr(classification, 'emergency_type'):
            logger.error("Classification object missing expected attributes")
            classification = create_fallback_classification(state['user_query'])

        # Update state with classification results
        state['emergency_type'] = classification.emergency_type
        state['vulnerability_level'] = classification.vulnerability_level
        state['symptoms'] = classification.symptoms

        # Save comprehensive emergency report
        report_data = {
            "report_id": state['report_id'],
            "timestamp": datetime.now().isoformat(),
            "user_query": state['user_query'],
            "emergency_type": classification.emergency_type,
            "vulnerability_level": classification.vulnerability_level,
            "symptoms": classification.symptoms,
            "suspected_condition": classification.suspected_condition,
            "location": state['location'],
            "requires_immediate_response": classification.requires_immediate_response
        }

        # Save the report
        if callable(save_emergency_report):
            save_emergency_report(report_data)

        # CHECK FOR ALERT GENERATION
        if classification.emergency_type in ['disease_outbreak', 'natural_disaster']:
            should_alert = alert_simulator.should_generate_alert(classification.emergency_type, report_data)

            if should_alert:
                # Get recent similar reports for alert generation
                recent_reports = alert_simulator._get_recent_similar_reports(
                    classification.emergency_type,
                    report_data,
                    alert_simulator.alert_thresholds[classification.emergency_type]['time_window_hours']
                )

                # Generate alert
                alert = alert_simulator.generate_alert(
                    classification.emergency_type,
                    recent_reports,
                    report_data
                )

                state['generated_alert'] = alert
                logger.info(f"ALERT GENERATED: {alert.get('title', 'Emergency Alert')}")

                # Store the alert in the active alerts database
                try:
                    from tools.emergency_tools import store_alert
                    store_alert(alert)
                    logger.info(f"Alert stored in active alerts database")
                except Exception as e:
                    logger.error(f"Error storing alert: {e}")

        logger.info(f"Emergency classified as {classification.emergency_type} with {classification.vulnerability_level} vulnerability")

    except Exception as e:
        logger.error(f"Error in classification: {e}\n{traceback.format_exc()}")
        state['error_message'] = "Classification system error occurred"

    return state
def create_fallback_classification(user_query: str) -> EmergencyClassification:
    """Create fallback classification when LLM fails"""
    query_lower = user_query.lower()
    
    # Simple keyword-based classification
    if any(word in query_lower for word in ['fever', 'cough', 'outbreak', 'epidemic', 'contagious', 'infection']):
        emergency_type = "disease_outbreak"
        symptoms = []
        if 'fever' in query_lower:
            symptoms.append('fever')
        if 'cough' in query_lower:
            symptoms.append('cough')
        if 'headache' in query_lower:
            symptoms.append('headache')
        suspected_condition = "viral infection"
    elif any(word in query_lower for word in ['flood', 'disaster', 'earthquake', 'cyclone', 'building collapse']):
        emergency_type = "natural_disaster"
        symptoms = ['disaster impact']
        suspected_condition = "natural disaster"
    else:
        emergency_type = "medical_emergency"
        symptoms = ['medical symptoms']
        suspected_condition = "medical condition"
    
    # Simple severity assessment
    if any(word in query_lower for word in ['critical', 'severe', 'emergency', 'urgent', 'can\'t breathe', 'unconscious']):
        vulnerability_level = "critical"
    elif any(word in query_lower for word in ['high', 'bad', 'terrible', 'awful', 'intense']):
        vulnerability_level = "high"
    elif any(word in query_lower for word in ['moderate', 'concerning', 'worried']):
        vulnerability_level = "medium"
    else:
        vulnerability_level = "medium"  # Default
    
    return EmergencyClassification(
        emergency_type=emergency_type,
        vulnerability_level=vulnerability_level,
        symptoms=symptoms,
        extracted_details=f"Fallback classification for: {user_query[:100]}",
        requires_immediate_response=vulnerability_level in ['critical', 'high'],
        suspected_condition=suspected_condition
    )

def alert_critical_services_node(state: EmergencyState) -> EmergencyState:
    """Enhanced emergency services alert with public alerts"""
    logger.info("Alerting emergency services for critical/high vulnerability case")
    
    try:
        # Handle generated alerts first
        response_parts = []
        
        if state.get('generated_alert'):
            alert = state['generated_alert']
            response_parts.extend([
                f"🚨 {alert['title']} 🚨",
                "",
                f"**ALERT LEVEL: {alert['alert_level']}**",
                "",
                f"**Summary:** {alert['summary']}",
                ""
            ])
            
            # Add details based on alert type
            if alert['alert_type'] == 'epidemic_warning':
                details = alert['details']
                response_parts.extend([
                    "**Outbreak Details:**",
                    f"• Total Cases: {details['total_cases']} in {details['time_period']}",
                    f"• Affected Area: {details['affected_area']}",
                    f"• Primary Symptoms: {', '.join(details['primary_symptoms'])}",
                    f"• Suspected Condition: {details['suspected_condition']}",
                    f"• Growth Rate: {details['growth_rate']}",
                    "",
                    "**Public Health Recommendations:**"
                ])
                for rec in alert['recommendations']:
                    response_parts.append(f"• {rec}")
                    
            elif alert['alert_type'] == 'disaster_alert':
                details = alert['details']
                response_parts.extend([
                    "**Disaster Details:**",
                    f"• Total Reports: {details['total_reports']} in {details['time_period']}",
                    f"• Affected Area: {details['affected_area']}",
                    f"• Primary Type: {details['primary_disaster_type']}",
                    f"• Severity Trend: {details['severity_trend']}",
                    "",
                    "**Immediate Actions Required:**"
                ])
                for action in alert['immediate_actions']:
                    response_parts.append(f"• {action}")
                
                if 'evacuation_info' in alert:
                    response_parts.extend([
                        "",
                        "**Evacuation Information:**",
                        f"• Centers: {', '.join(alert['evacuation_info']['evacuation_centers'])}",
                        f"• Transportation: {alert['evacuation_info']['transportation']}"
                    ])
            
            # Add emergency contacts
            response_parts.extend([
                "",
                "**Emergency Contacts:**"
            ])
            for service, number in alert['emergency_contacts'].items():
                response_parts.append(f"• {service.replace('_', ' ').title()}: {number}")
            
            response_parts.extend([
                "",
                f"Alert issued at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "Stay safe and follow official guidelines.",
                "",
                "---",
                ""
            ])
        
        # Now handle the individual case
        state['requires_booking'] = state['vulnerability_level'] in ['high', 'medium']
        
        # Individual response based on vulnerability
        if state['vulnerability_level'] == 'critical':
            response_parts.extend([
                "🆘 **CRITICAL EMERGENCY ALERT** 🆘",
                "",
                f"Report ID: {state['report_id']}",
                "Emergency services have been immediately dispatched to your location.",
                "",
                "**IMMEDIATE ACTIONS:**",
                "• Stay calm and in a safe location if possible",
                "• Keep your phone available for emergency responders",
                "• Do not move unless absolutely necessary",
                "",
                f"**Emergency Hotlines:**",
                f"• Ambulance: {config.emergency_hotlines['ambulance']}",
                f"• Emergency Services: {config.emergency_hotlines['disaster_management']}"
            ])
        elif state['vulnerability_level'] == 'high':
            response_parts.extend([
                "⚠️ **HIGH PRIORITY EMERGENCY** ⚠️",
                "",
                f"Report ID: {state['report_id']}",
                "Your situation requires urgent medical attention.",
                "Emergency services and nearest hospital have been alerted.",
                "",
                "An appointment will be arranged for you within the next 2 hours.",
                "Please remain available for confirmation calls.",
                "",
                "**WHILE WAITING:**",
                "• Monitor your symptoms closely",
                "• Avoid contact with others if infectious disease is suspected",
                "• Call 108 immediately if condition worsens"
            ])
        else:  # medium or low
            response_parts.extend([
                f"📋 **EMERGENCY REPORT FILED** - Priority: {state['vulnerability_level'].upper()}",
                "",
                f"Report ID: {state['report_id']}",
                f"Emergency Type: {state['emergency_type'].replace('_', ' ').title()}",
                "",
                "Your report has been logged and appropriate authorities notified.",
                "Follow the guidance provided and monitor your situation."
            ])
        
        state['final_response'] = "\n".join(response_parts)
        
        # Alert emergency services (mock)
        if callable(alert_emergency_services):
            alert_data = {
                "report_id": state['report_id'],
                "emergency_type": state['emergency_type'],
                "vulnerability_level": state['vulnerability_level'],
                "location": state['location'],
                "symptoms": state['symptoms'],
                "has_public_alert": state.get('generated_alert') is not None
            }
            alert_emergency_services(alert_data)
        
    except Exception as e:
        logger.error(f"Error alerting services: {e}")
        state['final_response'] = "Emergency services have been contacted. Help is on the way."
    
    return state

def provide_precautions_node(state: EmergencyState) -> EmergencyState:
    """Enhanced precautionary advice with alert awareness"""
    logger.info("Providing precautionary advice and monitoring guidance")
    
    try:
        response_parts = []
        
        # Handle generated alerts first
        if state.get('generated_alert'):
            alert = state['generated_alert']
            response_parts.extend([
                f"🚨 {alert['title']} 🚨",
                "",
                f"**ALERT LEVEL: {alert['alert_level']}**",
                f"**Summary:** {alert['summary']}",
                ""
            ])
            
            # Add appropriate recommendations from alert
            if 'recommendations' in alert:
                response_parts.extend([
                    "**Community Guidelines:**"
                ])
                for rec in alert['recommendations'][:3]:  # First 3 recommendations
                    response_parts.append(f"• {rec}")
                response_parts.append("")
        
        # Individual case handling
        response_parts.extend([
            f"📋 **YOUR EMERGENCY REPORT** - ID: {state['report_id']}",
            "",
            f"Type: {state['emergency_type'].replace('_', ' ').title()}",
            f"Vulnerability Level: {state['vulnerability_level'].title()}",
            ""
        ])
        
        # Add specific advice based on emergency type
        if state['emergency_type'] == 'disease_outbreak':
            response_parts.extend([
                "🦠 **DISEASE OUTBREAK PRECAUTIONS:**",
                "• Monitor symptoms closely for changes",
                "• Maintain isolation if infectious symptoms present",
                "• Track daily temperature and symptom severity",
                "• Seek immediate care if symptoms worsen"
            ])
        elif state['emergency_type'] == 'natural_disaster':
            response_parts.extend([
                "🌊 **NATURAL DISASTER SAFETY:**",
                "• Stay in safe, elevated location if flooding",
                "• Keep emergency supplies accessible",
                "• Monitor official disaster management updates",
                "• Be prepared for evacuation if conditions worsen"
            ])
        elif state['emergency_type'] == 'medical_emergency':
            response_parts.extend([
                "🏥 **MEDICAL EMERGENCY GUIDANCE:**",
                "• Monitor your condition continuously",
                "• Keep emergency contacts readily available",
                "• Note any changes in symptoms",
                "• Follow medical advice strictly"
            ])
        
        # Add monitoring schedule
        response_parts.extend([
            "",
            "📅 **MONITORING SCHEDULE:**",
            "• Report significant changes immediately",
            "• Daily symptom check recommended",
            "• Follow up in 24-48 hours if no improvement",
            "",
            f"🆘 **Emergency Contact: {config.emergency_hotlines['ambulance']} (if condition worsens)**"
        ])
        
        state['final_response'] = "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"Error providing precautions: {e}")
        state['final_response'] = "Your report has been filed. Please monitor your condition and contact emergency services if symptoms worsen."
    
    return state

def book_urgent_appointment_node(state: EmergencyState) -> EmergencyState:
    """Book urgent appointment for high/medium vulnerability cases"""
    logger.info("Booking urgent appointment for emergency case")
    
    try:
        # Prepare booking data
        booking_query = f"Urgent appointment needed for {', '.join(state['symptoms'])} - Emergency Report ID: {state['report_id']}"
        
        booking_state = {
            "user_query": booking_query,
            "symptoms": state['symptoms'],
            "urgency": "High" if state['vulnerability_level'] in ['critical', 'high'] else "Medium",
            "specialty": determine_specialty(state['symptoms'], state['emergency_type']),
            "emergency_context": True,
            "report_id": state['report_id']
        }
        
        # Use booking agent if available
        try:
            booking_result = booking_agent_app(booking_state)
            state['final_response'] += f"\n\n🏥 **URGENT APPOINTMENT BOOKING:**\n{booking_result.get('final_response', 'Appointment booking initiated')}"
        except:
            state['final_response'] += "\n\n🏥 **URGENT APPOINTMENT BOOKING:**\nAppointment booking will be handled manually. You will receive a call shortly."
        
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        state['final_response'] += "\n\nAppointment booking will be handled manually. You will receive a call shortly."
    
    return state

def determine_specialty(symptoms: List[str], emergency_type: str) -> str:
    """Determine appropriate medical specialty"""
    symptom_text = ' '.join(symptoms).lower()
    
    if emergency_type == 'disease_outbreak':
        if any(term in symptom_text for term in ['fever', 'infection', 'rash']):
            return "Infectious Disease"
    elif emergency_type == 'natural_disaster':
        if any(term in symptom_text for term in ['injury', 'wound', 'fracture']):
            return "Emergency Medicine"
    
    return "Emergency Medicine"

def error_handler_node(state: EmergencyState) -> EmergencyState:
    """Handle system errors"""
    logger.error(f"Emergency system error: {state.get('error_message', 'Unknown error')}")
    
    state['final_response'] = f"""🚨 **SYSTEM ERROR - EMERGENCY PROTOCOLS ACTIVATED** 🚨

Report ID: {state.get('report_id', 'N/A')}

Despite technical difficulties, your emergency has been logged.

**IMMEDIATE ACTIONS:**
• Call emergency services directly: 108
• Contact nearest hospital
• Do not wait for system recovery in critical situations

We apologize for the technical issue during your emergency."""
    
    return state

# --- Conditional Decision Functions ---

def decide_response_level(state: EmergencyState) -> str:
    """Decide response level based on vulnerability"""
    if state.get('error_message'):
        return "error_handler"
    
    vulnerability = state.get('vulnerability_level', '').lower()
    
    if vulnerability in ['critical', 'high']:
        return "alert_services"
    elif vulnerability == 'medium':
        return "provide_precautions_and_book"
    else:
        return "provide_precautions"

def should_book_appointment(state: EmergencyState) -> str:
    """Determine if appointment booking is needed"""
    if state.get('requires_booking'):
        return "book_appointment"
    return "end"

# --- Assemble Enhanced Workflow ---

def create_emergency_workflow() -> StateGraph:
    """Create comprehensive emergency response workflow with alert simulation"""
    workflow = StateGraph(EmergencyState)
    
    # Add nodes
    workflow.add_node("collect_and_classify", collect_and_classify_node)
    workflow.add_node("alert_services", alert_critical_services_node)
    workflow.add_node("provide_precautions", provide_precautions_node)
    workflow.add_node("provide_precautions_and_book", provide_precautions_node)
    workflow.add_node("book_appointment", book_urgent_appointment_node)
    workflow.add_node("error_handler", error_handler_node)
    
    # Set entry point
    workflow.set_entry_point("collect_and_classify")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "collect_and_classify",
        decide_response_level,
        {
            "alert_services": "alert_services",
            "provide_precautions": "provide_precautions",
            "provide_precautions_and_book": "provide_precautions_and_book",
            "error_handler": "error_handler"
        }
    )
    
    # Terminal edges
    workflow.add_edge("alert_services", END)
    workflow.add_edge("provide_precautions", END)
    workflow.add_edge("error_handler", END)
    
    # Booking flow for medium vulnerability
    workflow.add_conditional_edges(
        "provide_precautions_and_book",
        should_book_appointment,
        {
            "book_appointment": "book_appointment",
            "end": END
        }
    )
    
    workflow.add_edge("book_appointment", END)
    
    return workflow

# Create the enhanced emergency agent with alert simulation
emergency_agent_app = create_emergency_workflow().compile()

# --- Alert Display Functions for Chat Interface ---

def get_active_alerts(location: str = "warangal") -> List[Dict[str, Any]]:
    """Get currently active alerts for display in chat"""
    try:
        from tools.emergency_tools import get_active_alerts as get_stored_alerts
        return get_stored_alerts()
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        return []

def format_alert_for_display(alert: Dict[str, Any]) -> str:
    """Format alert for chat display"""
    try:
        formatted_parts = [
            f"🚨 **{alert.get('title', 'Emergency Alert')}** 🚨",
            f"**Level:** {alert.get('alert_level', 'UNKNOWN')}",
            f"**Summary:** {alert.get('summary', 'Emergency situation detected')}",
            ""
        ]
        
        # Add key details
        details = alert.get('details', {})
        if alert.get('alert_type') == 'epidemic_warning':
            formatted_parts.extend([
                "**Outbreak Information:**",
                f"• Cases: {details.get('total_cases', 'Unknown')} in {details.get('time_period', 'recent period')}",
                f"• Area: {details.get('affected_area', 'Local area')}",
                f"• Primary symptoms: {', '.join(details.get('primary_symptoms', ['Unknown']))}",
                ""
            ])
        elif alert.get('alert_type') == 'disaster_alert':
            formatted_parts.extend([
                "**Disaster Information:**",
                f"• Reports: {details.get('total_reports', 'Multiple')} in {details.get('time_period', 'recent period')}",
                f"• Area: {details.get('affected_area', 'Local area')}",
                f"• Type: {details.get('primary_disaster_type', 'Natural disaster')}",
                ""
            ])
        
        # Add top recommendations/actions
        if alert.get('recommendations'):
            formatted_parts.append("**Key Recommendations:**")
            for rec in alert['recommendations'][:3]:
                formatted_parts.append(f"• {rec}")
        elif alert.get('immediate_actions'):
            formatted_parts.append("**Immediate Actions:**")
            for action in alert['immediate_actions'][:3]:
                formatted_parts.append(f"• {action}")
        
        formatted_parts.extend([
            "",
            f"*Alert active until: {datetime.fromisoformat(alert.get('expires_at', datetime.now().isoformat())).strftime('%Y-%m-%d %H:%M')}*"
        ])
        
        return "\n".join(formatted_parts)
        
    except Exception as e:
        logger.error(f"Error formatting alert: {e}")
        return "Emergency alert active - please check official channels for details."

# --- Testing and Simulation Functions ---

def simulate_outbreak_scenario():
    """Simulate a disease outbreak for testing"""
    logger.info("Simulating disease outbreak scenario...")
    
    # Create multiple related reports
    outbreak_symptoms = [
        ["fever", "cough", "fatigue"],
        ["fever", "headache", "body ache"],
        ["fever", "cough", "difficulty breathing"],
        ["fever", "nausea", "weakness"],
        ["high fever", "cough", "fatigue"],
        ["fever", "headache", "cough"]
    ]
    
    test_queries = [
        "I have high fever and persistent cough for 3 days, feeling very weak",
        "Fever and severe headache, body is aching all over",
        "High fever with cough and having trouble breathing properly",
        "Fever and nausea, feeling extremely weak and tired",
        "Very high fever 102F and continuous cough, fatigue",
        "Fever headache and cough, many people in my area seem sick"
    ]
    
    results = []
    for i, query in enumerate(test_queries):
        try:
            test_state = {"user_query": query}
            result = emergency_agent_app.invoke(test_state)
            results.append(result)
            
            logger.info(f"Report {i+1} processed - Alert generated: {result.get('generated_alert') is not None}")
            
            if result.get('generated_alert'):
                logger.info(f"ALERT: {result['generated_alert']['title']}")
                break  # Stop after first alert
                
        except Exception as e:
            logger.error(f"Error in simulation report {i+1}: {e}")
    
    return results

def simulate_disaster_scenario():
    """Simulate a natural disaster for testing"""
    logger.info("Simulating natural disaster scenario...")
    
    test_queries = [
        "Heavy flooding in our area, water entering homes",
        "Major flooding, roads are completely blocked",
        "Severe flood situation, need immediate help",
        "Flood water rising, evacuation needed"
    ]
    
    results = []
    for i, query in enumerate(test_queries):
        try:
            test_state = {"user_query": query}
            result = emergency_agent_app.invoke(test_state)
            results.append(result)
            
            if result.get('generated_alert'):
                logger.info(f"DISASTER ALERT: {result['generated_alert']['title']}")
                break
                
        except Exception as e:
            logger.error(f"Error in disaster simulation {i+1}: {e}")
    
    return results

# --- Main Application Interface ---

class EmergencySystemInterface:
    """Main interface for the emergency system with alert capabilities"""
    
    def __init__(self):
        self.system = emergency_agent_app
        self.alert_display_enabled = True
        self.last_alert_check = datetime.now()
        self.alert_check_interval = timedelta(minutes=5)  # Check for alerts every 5 minutes
    
    def process_emergency_report(self, user_query: str) -> Dict[str, Any]:
        """Process an emergency report and return response with any alerts"""
        try:
            # Process the emergency report
            state = {"user_query": user_query}
            result = self.system.invoke(state)
            
            # Check for active alerts if enabled
            active_alerts = []
            if self.alert_display_enabled:
                active_alerts = get_active_alerts()
            
            return {
                "emergency_response": result.get('final_response', 'Emergency processed'),
                "report_id": result.get('report_id'),
                "emergency_type": result.get('emergency_type'),
                "vulnerability_level": result.get('vulnerability_level'),
                "generated_alert": result.get('generated_alert'),
                "active_alerts": active_alerts,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing emergency report: {e}")
            return {
                "emergency_response": "Emergency system error - please call 108 directly for immediate assistance",
                "status": "error",
                "error": str(e)
            }
    
    def get_current_alerts(self) -> List[str]:
        """Get formatted current alerts for display"""
        try:
            alerts = get_active_alerts()
            return [format_alert_for_display(alert) for alert in alerts]
        except Exception as e:
            logger.error(f"Error getting current alerts: {e}")
            return []
    
    def run_simulation(self, scenario: str = "outbreak") -> List[Dict[str, Any]]:
        """Run emergency scenario simulation"""
        logger.info(f"Starting {scenario} simulation...")
        logger.info(f"Current database state: {len(EMERGENCY_REPORTS_DB)} emergency reports, {len(EPIDEMIC_TRACKING_DB)} epidemic reports")
        
        if scenario == "outbreak":
            return simulate_outbreak_scenario()
        elif scenario == "disaster":
            return simulate_disaster_scenario()
        else:
            logger.error(f"Unknown scenario: {scenario}")
            return []

# Initialize the emergency system interface
emergency_system = EmergencySystemInterface()

# Export for testing
if __name__ == "__main__":
    # Test the enhanced system with alert simulation
    print("=== Testing Emergency System with Alert Simulation ===\n")
    
    # Test individual report
    test_query = "High fever, cough, and difficulty breathing - multiple people in my neighborhood have similar symptoms"
    result = emergency_system.process_emergency_report(test_query)
    
    print("Individual Report Response:")
    print(result['emergency_response'])
    
    if result.get('generated_alert'):
        print(f"\n🚨 ALERT GENERATED: {result['generated_alert']['title']}")
    
    print("\n" + "="*60 + "\n")
    
    # Test outbreak simulation
    print("Running outbreak simulation...")
    outbreak_results = emergency_system.run_simulation("outbreak")
    print(f"Processed {len(outbreak_results)} outbreak reports")
    
    # Check for any alerts generated
    alerts_found = [r for r in outbreak_results if r.get('generated_alert')]
    if alerts_found:
        print(f"Alert generated after {len(outbreak_results)} reports")
        alert = alerts_found[0]['generated_alert']
        print(f"Alert: {alert['title']}")
        print(f"Level: {alert['alert_level']}")
    
    print("\n" + "="*60 + "\n")
    
    # Show current active alerts
    current_alerts = emergency_system.get_current_alerts()
    if current_alerts:
        print("Current Active Alerts:")
        for alert in current_alerts:
            print(alert)
            print("-" * 40)
    else:
        print("No active alerts currently")