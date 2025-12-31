import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import random
import math


# Create cache directory if it doesn't exist
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(CACHE_DIR, "emergency_db_cache.json")

logger = logging.getLogger(__name__)
# REMOVED @tool decorators - these are now regular Python functions


class EmergencyDatabase:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self._load_from_cache()
        print(f"Initialized EmergencyDatabase from {cache_file}.")

    def _load_from_cache(self):
        """Loads data from the JSON cache file if it exists."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.emergency_reports = data.get("emergency_reports", [])
                    self.epidemic_reports = data.get("epidemic_reports", [])
                    self.resource_availability = data.get("resource_availability", {})
                logger.info(f"Loaded {len(self.emergency_reports)} reports from cache.")
            else:
                self.reset_data()
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading cache file {self.cache_file}: {e}. Starting fresh.")
            self.reset_data()

    def _save_to_cache(self):
        """Saves the current data to the JSON cache file."""
        try:
            with open(self.cache_file, 'w') as f:
                data = {
                    "emergency_reports": self.emergency_reports,
                    "epidemic_reports": self.epidemic_reports,
                    "resource_availability": self.resource_availability
                }
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving to cache file {self.cache_file}: {e}")

    def save_report(self, report_data: dict):
        report_data['created_at'] = datetime.now().isoformat()
        self.emergency_reports.append(report_data)
        if report_data.get('emergency_type') == 'disease_outbreak':
            self.epidemic_reports.append(report_data)
        self._save_to_cache() # <-- Save after every change
        logger.info(f"Report {report_data.get('report_id')} saved and cached.")

    def reset_data(self):
        self.emergency_reports = []
        self.epidemic_reports = []
        self.resource_availability = {}
        self._save_to_cache() # <-- Save after resetting
        logger.warning("Emergency databases have been reset and cache cleared.")
    
    def get_recent_reports(self, report_type: str, cutoff_time: datetime):
        """Get recent reports based on type and time cutoff"""
        if report_type == 'emergency':
            return [r for r in self.emergency_reports 
                   if datetime.fromisoformat(r.get('created_at', r.get('timestamp', ''))) > cutoff_time]
        elif report_type == 'epidemic':
            return [r for r in self.epidemic_reports 
                   if datetime.fromisoformat(r.get('created_at', r.get('timestamp', ''))) > cutoff_time]
        return []

# --- Create a single instance of the database ---
db_instance = EmergencyDatabase(cache_file=CACHE_FILE)

# Legacy database variables for backward compatibility
EMERGENCY_REPORTS_DB = db_instance.emergency_reports
EPIDEMIC_TRACKING_DB = db_instance.epidemic_reports
RESOURCE_AVAILABILITY_DB = db_instance.resource_availability
POPULATION_DATA = {
    "warangal": {
        "total_population": 811844,
        "area_km2": 406,
        "districts": {
            "warangal_urban": {"population": 704570, "area": 135},
            "warangal_rural": {"population": 107274, "area": 271}
        },
        "vulnerable_groups": {
            "children_under_5": 65000,
            "elderly_over_65": 58000,
            "immunocompromised": 25000,
            "pregnant_women": 12000
        }
    }
}

def save_emergency_report(report_data: dict) -> str:
    """
    Save comprehensive emergency report with analytics data to database.
    Supports disease outbreak and natural disaster tracking.
    """
    try:
        # Add timestamp and additional metadata
        report_data['status'] = 'active'
        report_data['follow_up_required'] = report_data.get('vulnerability_level') in ['critical', 'high']
        
        # Use the persistent database instance
        db_instance.save_report(report_data)
        
        logger.info(f"Emergency report {report_data['report_id']} saved successfully")
        logger.info(f"Report type: {report_data.get('emergency_type', 'unknown')}")
        logger.info(f"Vulnerability: {report_data.get('vulnerability_level', 'unknown')}")
        
        return f"Emergency report {report_data['report_id']} successfully filed and logged in the system."
        
    except Exception as e:
        logger.error(f"Error saving emergency report: {e}")
        return f"Error filing report: {str(e)}"

def alert_emergency_services(alert_data: dict) -> str:
    """
    Alert emergency services with comprehensive situation data.
    Dispatches appropriate response based on emergency type and analytics.
    """
    try:
        report_id = alert_data.get('report_id', 'unknown')
        emergency_type = alert_data.get('emergency_type', 'unknown')
        vulnerability = alert_data.get('vulnerability_level', 'unknown')
        location = alert_data.get('location', {})
        
        logger.info(f"--- EMERGENCY SERVICES ALERT ---")
        logger.info(f"Report ID: {report_id}")
        logger.info(f"Type: {emergency_type}")
        logger.info(f"Vulnerability: {vulnerability}")
        logger.info(f"Location: {location}")
        logger.info(f"Public Alert Generated: {alert_data.get('has_public_alert', False)}")
        
        # Simulate different response types based on emergency
        response_teams = []
        
        if emergency_type == 'disease_outbreak':
            response_teams.extend([
                "Epidemic Response Team",
                "Mobile Testing Unit",
                "Contact Tracing Team"
            ])
            if vulnerability in ['critical', 'high']:
                response_teams.append("Emergency Ambulance")
        
        elif emergency_type == 'natural_disaster':
            response_teams.extend([
                "Disaster Response Team",
                "Search and Rescue",
                "Emergency Shelter Coordination"
            ])
            if vulnerability == 'critical':
                response_teams.extend(["Fire Department", "Emergency Medical Team"])
        
        else:  # medical_emergency
            response_teams.extend([
                "Emergency Ambulance",
                "Paramedic Team"
            ])
            if vulnerability == 'critical':
                response_teams.append("Advanced Life Support Unit")
        
        # Log dispatch
        for team in response_teams:
            logger.info(f"Dispatching: {team}")
        
        # Calculate estimated response time
        estimated_time = alert_data.get('estimated_response_time', 
            calculate_response_time(location, emergency_type, vulnerability))
        
        logger.info(f"Estimated response time: {estimated_time} minutes")
        
        # Update resource allocation
        update_resource_allocation(location, response_teams)
        
        return f"Emergency services alerted. {len(response_teams)} response units dispatched. ETA: {estimated_time} minutes."
        
    except Exception as e:
        logger.error(f"Error alerting emergency services: {e}")
        return "Emergency services have been notified despite system error."

def calculate_response_time(location: Dict, emergency_type: str, vulnerability: str) -> int:
    """Calculate estimated response time based on multiple factors"""
    # Base response times by emergency type
    base_times = {
        'medical_emergency': 8,
        'disease_outbreak': 15,
        'natural_disaster': 20
    }
    
    base_time = base_times.get(emergency_type, 10)
    
    # Vulnerability multiplier
    vulnerability_multipliers = {
        'critical': 0.7,  # Faster response for critical
        'high': 0.9,
        'medium': 1.1,
        'low': 1.3
    }
    
    multiplier = vulnerability_multipliers.get(vulnerability, 1.0)
    
    # Location factors (mock implementation)
    urban_factor = 1.0 if location.get('district', '') == 'warangal_urban' else 1.4
    
    # Current load factor (mock - would be real-time in actual system)
    current_load = random.uniform(0.8, 1.3)
    
    final_time = int(base_time * multiplier * urban_factor * current_load)
    return max(final_time, 3)  # Minimum 3 minutes

def update_resource_allocation(location: Dict, response_teams: List[str]):
    """Update resource allocation tracking"""
    district = location.get('district', 'warangal')
    
    if district not in RESOURCE_AVAILABILITY_DB:
        RESOURCE_AVAILABILITY_DB[district] = {
            'ambulances_available': 12,
            'response_teams_available': 8,
            'hospital_beds_available': 150,
            'last_updated': datetime.now().isoformat()
        }
    
    # Simulate resource allocation
    resources = RESOURCE_AVAILABILITY_DB[district]
    if 'Emergency Ambulance' in response_teams:
        resources['ambulances_available'] = max(0, resources['ambulances_available'] - 1)
    
    resources['response_teams_available'] = max(0, resources['response_teams_available'] - len(response_teams))
    resources['last_updated'] = datetime.now().isoformat()

def calculate_epidemic_metrics(location_data: dict) -> dict:
    """
    Calculate comprehensive epidemic tracking metrics including:
    - Population density vs case density
    - Case growth rate over time
    - Migration flow impact
    - Resource availability index
    """
    try:
        district = location_data.get('district', 'warangal')
        
        # Get population data
        pop_data = POPULATION_DATA.get('warangal', {})
        
        # Calculate population density
        population_density = calculate_population_density_metrics(district)
        
        # Calculate case density from recent reports
        case_density = calculate_case_density_metrics(district)
        
        # Calculate growth rate
        growth_metrics = calculate_case_growth_metrics(district)
        
        # Migration patterns
        migration_data = calculate_migration_patterns(district)
        
        # Resource availability
        resource_index = calculate_resource_availability_index(district)
        
        metrics = {
            "location": district,
            "timestamp": datetime.now().isoformat(),
            "population_metrics": population_density,
            "case_metrics": case_density,
            "growth_analysis": growth_metrics,
            "migration_analysis": migration_data,
            "resource_availability": resource_index,
            "risk_assessment": calculate_overall_risk(population_density, case_density, growth_metrics)
        }
        
        logger.info(f"Epidemic metrics calculated for {district}")
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating epidemic metrics: {e}")
        return {"error": f"Failed to calculate metrics: {str(e)}"}

def calculate_population_density_metrics(district: str) -> dict:
    """Calculate detailed population density metrics"""
    pop_data = POPULATION_DATA['warangal']
    
    district_data = pop_data['districts'].get(f'{district}_urban', pop_data['districts']['warangal_urban'])
    
    return {
        "people_per_km2": district_data['population'] / district_data['area'],
        "total_population": district_data['population'],
        "vulnerable_population": pop_data['vulnerable_groups'],
        "vulnerability_percentage": sum(pop_data['vulnerable_groups'].values()) / pop_data['total_population'] * 100,
        "density_category": categorize_density(district_data['population'] / district_data['area'])
    }

def categorize_density(density: float) -> str:
    """Categorize population density"""
    if density > 5000:
        return "very_high"
    elif density > 2000:
        return "high"
    elif density > 1000:
        return "medium"
    else:
        return "low"

def calculate_case_density_metrics(district: str) -> dict:
    """Calculate case density from stored reports"""
    # Filter reports for the district in last 7 days
    recent_reports = [
        r for r in EPIDEMIC_TRACKING_DB 
        if r.get('location', {}).get('district') == district
        and datetime.fromisoformat(r['timestamp']) > datetime.now() - timedelta(days=7)
    ]
    
    # Calculate cases per 1000 population
    district_population = POPULATION_DATA['warangal']['districts'].get(f'{district}_urban', {}).get('population', 700000)
    cases_per_1000 = len(recent_reports) / district_population * 1000
    
    # Symptom clustering analysis
    symptom_clusters = analyze_symptom_clusters(recent_reports)
    
    return {
        "total_cases_7_days": len(recent_reports),
        "cases_per_1000_population": cases_per_1000,
        "cases_last_24h": len([r for r in recent_reports if datetime.fromisoformat(r['timestamp']) > datetime.now() - timedelta(days=1)]),
        "symptom_clusters": symptom_clusters,
        "hotspot_areas": identify_hotspots(recent_reports),
        "cluster_risk": calculate_cluster_risk(recent_reports)
    }

def analyze_symptom_clusters(reports: List[dict]) -> dict:
    """Analyze symptom clustering patterns"""
    symptom_counts = {}
    symptom_combinations = {}
    
    for report in reports:
        symptoms = report.get('symptoms', [])
        for symptom in symptoms:
            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
        
        # Track symptom combinations
        symptom_combo = tuple(sorted(symptoms))
        if len(symptom_combo) > 1:
            symptom_combinations[symptom_combo] = symptom_combinations.get(symptom_combo, 0) + 1
    
    return {
        "most_common_symptoms": dict(sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
        "symptom_combinations": dict(sorted(symptom_combinations.items(), key=lambda x: x[1], reverse=True)[:3])
    }

def identify_hotspots(reports: List[dict]) -> List[dict]:
    """Identify geographical hotspots"""
    # Mock implementation - would use actual geolocation clustering
    hotspots = []
    
    if len(reports) > 10:
        hotspots.append({
            "area": "Central Warangal",
            "case_count": len(reports) // 2,
            "radius_km": 2.5,
            "risk_level": "high" if len(reports) > 20 else "medium"
        })
    
    return hotspots

def calculate_cluster_risk(reports: List[dict]) -> float:
    """Calculate clustering risk score (0-1)"""
    if len(reports) < 5:
        return 0.1
    
    # Mock calculation based on report frequency and symptom similarity
    temporal_clustering = len(reports[-10:]) / 10 if len(reports) >= 10 else len(reports) / 10
    symptom_similarity = 0.6  # Would calculate actual symptom similarity
    
    return min(temporal_clustering * symptom_similarity * 1.5, 1.0)

def calculate_case_growth_metrics(district: str) -> dict:
    """Calculate case growth patterns over time"""
    # Get reports for last 14 days
    reports = [
        r for r in EPIDEMIC_TRACKING_DB 
        if r.get('location', {}).get('district') == district
        and datetime.fromisoformat(r['timestamp']) > datetime.now() - timedelta(days=14)
    ]
    
    if len(reports) < 2:
        return {
            "daily_growth_rate": 0.0,
            "doubling_time_days": None,
            "trend": "insufficient_data",
            "r_effective": None
        }
    
    # Group by day
    daily_counts = {}
    for report in reports:
        date = datetime.fromisoformat(report['timestamp']).date()
        daily_counts[date] = daily_counts.get(date, 0) + 1
    
    # Calculate growth rate (simplified)
    dates = sorted(daily_counts.keys())
    if len(dates) >= 2:
        recent_avg = sum(daily_counts[d] for d in dates[-3:]) / min(3, len(dates))
        earlier_avg = sum(daily_counts[d] for d in dates[:3]) / min(3, len(dates))
        
        growth_rate = (recent_avg - earlier_avg) / max(earlier_avg, 1) if earlier_avg > 0 else 0
    else:
        growth_rate = 0
    
    # Estimate doubling time
    doubling_time = None
    if growth_rate > 0:
        doubling_time = math.log(2) / math.log(1 + growth_rate) if growth_rate > 0 else None
    
    # Estimate R effective (reproduction number) - simplified
    r_effective = 1 + growth_rate if growth_rate is not None else 1.0
    
    # Determine trend
    trend = "increasing" if growth_rate > 0.05 else "decreasing" if growth_rate < -0.05 else "stable"
    
    return {
        "daily_growth_rate": round(growth_rate, 3),
        "doubling_time_days": round(doubling_time, 1) if doubling_time else None,
        "trend": trend,
        "r_effective": round(r_effective, 2),
        "total_cases_14_days": len(reports)
    }

def calculate_migration_patterns(district: str) -> dict:
    """Calculate migration and population movement patterns"""
    # Mock implementation - would integrate with transport data, mobile data, etc.
    return {
        "daily_population_flow": {
            "incoming": random.randint(8000, 15000),
            "outgoing": random.randint(7000, 12000),
            "net_flow": random.randint(-2000, 3000)
        },
        "transport_connectivity": {
            "railway_connections": 5,
            "highway_access": 3,
            "airport_proximity_km": 85
        },
        "movement_risk_factors": {
            "festival_season": False,
            "harvest_season": True,
            "school_holidays": False,
            "wedding_season": True
        },
        "containment_feasibility": 0.65,  # 0-1 scale
        "border_control_points": 8
    }

def calculate_resource_availability_index(district: str) -> dict:
    """Calculate comprehensive resource availability"""
    # Mock data - would integrate with hospital systems, supply chains, etc.
    base_resources = RESOURCE_AVAILABILITY_DB.get(district, {
        'ambulances_available': 12,
        'response_teams_available': 8,
        'hospital_beds_available': 150
    })
    
    return {
        "healthcare_capacity": {
            "hospital_beds_total": 200,
            "hospital_beds_available": base_resources['hospital_beds_available'],
            "icu_beds_total": 25,
            "icu_beds_available": 15,
            "ventilators_available": 8,
            "isolation_wards": 3
        },
        "emergency_response": {
            "ambulances_total": 15,
            "ambulances_available": base_resources['ambulances_available'],
            "response_teams_total": 12,
            "response_teams_available": base_resources['response_teams_available'],
            "avg_response_time_minutes": 8.5
        },
        "medical_supplies": {
            "ppe_stock_days": 45,
            "medicine_stock_days": 30,
            "test_kits_available": 500,
            "oxygen_supply_days": 15
        },
        "human_resources": {
            "doctors_available": 45,
            "nurses_available": 120,
            "paramedics_available": 28,
            "specialists_available": 12
        },
        "overall_capacity_score": calculate_capacity_score(base_resources)
    }

def calculate_capacity_score(resources: dict) -> float:
    """Calculate overall capacity score (0-1)"""
    # Simplified scoring based on available resources
    bed_score = resources['hospital_beds_available'] / 200
    ambulance_score = resources['ambulances_available'] / 15
    team_score = resources['response_teams_available'] / 12
    
    return round((bed_score + ambulance_score + team_score) / 3, 2)

def calculate_overall_risk(pop_metrics: dict, case_metrics: dict, growth_metrics: dict) -> dict:
    """Calculate overall epidemic risk assessment"""
    # Risk factors
    density_risk = 0.8 if pop_metrics['density_category'] in ['high', 'very_high'] else 0.4
    case_risk = min(case_metrics['cases_per_1000_population'] / 10, 1.0)
    growth_risk = min(abs(growth_metrics.get('daily_growth_rate', 0)) * 10, 1.0)
    cluster_risk = case_metrics.get('cluster_risk', 0)
    
    overall_risk = (density_risk + case_risk + growth_risk + cluster_risk) / 4
    
    risk_level = "critical" if overall_risk > 0.8 else "high" if overall_risk > 0.6 else "medium" if overall_risk > 0.4 else "low"
    
    return {
        "overall_risk_score": round(overall_risk, 2),
        "risk_level": risk_level,
        "contributing_factors": {
            "population_density": density_risk,
            "case_density": case_risk,
            "growth_rate": growth_risk,
            "clustering": cluster_risk
        },
        "recommendations": generate_risk_recommendations(risk_level, overall_risk)
    }

def generate_risk_recommendations(risk_level: str, risk_score: float) -> List[str]:
    """Generate recommendations based on risk level"""
    recommendations = []
    
    if risk_level == "critical":
        recommendations.extend([
            "Implement immediate containment measures",
            "Activate emergency response protocols",
            "Increase testing and contact tracing capacity",
            "Consider movement restrictions"
        ])
    elif risk_level == "high":
        recommendations.extend([
            "Enhance surveillance and monitoring",
            "Prepare emergency response systems",
            "Increase public health messaging",
            "Monitor hospital capacity closely"
        ])
    elif risk_level == "medium":
        recommendations.extend([
            "Continue active monitoring",
            "Maintain preventive measures",
            "Regular capacity assessments",
            "Community awareness programs"
        ])
    else:
        recommendations.extend([
            "Routine surveillance",
            "Maintain preparedness",
            "Regular health education"
        ])
    
    return recommendations

def get_resource_availability(location_data: dict) -> dict:
    """Get current resource availability for the location"""
    try:
        district = location_data.get('district', 'warangal')
        return calculate_resource_availability_index(district)
    except Exception as e:
        logger.error(f"Error getting resource availability: {e}")
        return {"error": f"Failed to get resource data: {str(e)}"}

def track_migration_patterns(location_data: dict) -> dict:
    """Track population migration and movement patterns"""
    try:
        district = location_data.get('district', 'warangal')
        return calculate_migration_patterns(district)
    except Exception as e:
        logger.error(f"Error tracking migration patterns: {e}")
        return {"error": f"Failed to track migration: {str(e)}"}

def get_population_density_data(location_data: dict) -> dict:
    """Get population density and demographic data"""
    try:
        district = location_data.get('district', 'warangal')
        return calculate_population_density_metrics(district)
    except Exception as e:
        logger.error(f"Error getting population data: {e}")
        return {"error": f"Failed to get population data: {str(e)}"}

# Utility function for testing
def generate_test_data():
    """Generate test data for demonstration"""
    # Add some test epidemic reports
    test_symptoms = [
        ["fever", "cough", "fatigue"],
        ["fever", "headache", "body_ache"],
        ["fever", "nausea", "weakness"],
        ["cough", "breathing_difficulty"],
        ["fever", "rash", "headache"]
    ]
    
    for i, symptoms in enumerate(test_symptoms):
        test_report = {
            "report_id": f"TEST-{i:03d}",
            "timestamp": (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat(),
            "symptoms": symptoms,
            "location": {"district": "warangal", "lat": 17.9689, "lon": 79.5894},
            "suspected_condition": "viral_infection"
        }
        EPIDEMIC_TRACKING_DB.append(test_report)
    
    logger.info("Test data generated for epidemic tracking")

# Clear any existing test data and generate fresh data
def reset_and_generate_test_data():
    """Reset databases and generate fresh test data"""
    db_instance.reset_data()
    generate_test_data()
    logger.info("Databases reset and fresh test data generated")

ACTIVE_ALERTS_DB = []

def store_alert(alert: dict) -> None:
    """Store an alert in the active alerts database"""
    global ACTIVE_ALERTS_DB
    
    try:
        # Add storage timestamp
        alert['stored_at'] = datetime.now().isoformat()
        
        # Remove expired alerts first
        current_time = datetime.now()
        ACTIVE_ALERTS_DB = [
            a for a in ACTIVE_ALERTS_DB 
            if datetime.fromisoformat(a.get('expires_at', current_time.isoformat())) > current_time
        ]
        
        # Add new alert
        ACTIVE_ALERTS_DB.append(alert)
        
        logger.info(f"Alert stored: {alert.get('title', 'Unknown')} - Level: {alert.get('alert_level', 'Unknown')}")
        logger.info(f"Total active alerts: {len(ACTIVE_ALERTS_DB)}")
        
    except Exception as e:
        logger.error(f"Error storing alert: {e}")

def get_active_alerts() -> List[dict]:
    """Get currently active alerts"""
    global ACTIVE_ALERTS_DB
    
    try:
        current_time = datetime.now()
        
        # Filter out expired alerts
        active_alerts = [
            alert for alert in ACTIVE_ALERTS_DB 
            if datetime.fromisoformat(alert.get('expires_at', current_time.isoformat())) > current_time
        ]
        
        # Update the global list
        ACTIVE_ALERTS_DB = active_alerts
        
        logger.info(f"Retrieved {len(active_alerts)} active alerts")
        return active_alerts
        
    except Exception as e:
        logger.error(f"Error retrieving active alerts: {e}")
        return []

def clear_all_alerts() -> None:
    """Clear all alerts (for testing)"""
    global ACTIVE_ALERTS_DB
    ACTIVE_ALERTS_DB.clear()
    logger.info("All alerts cleared")

# Add this function to reset everything including alerts
def reset_all_simulation_data():
    """Reset all simulation data including alerts"""
    global ACTIVE_ALERTS_DB
    
    db_instance.reset_data()
    ACTIVE_ALERTS_DB.clear()
    
    logger.info("All simulation data reset including alerts")

if __name__ == "__main__":
    # Generate test data and run sample calculations
    reset_and_generate_test_data()
    
    sample_location = {"district": "warangal", "lat": 17.9689, "lon": 79.5894}
    
    print("Sample Epidemic Metrics:")
    metrics = calculate_epidemic_metrics(sample_location)
    print(json.dumps(metrics, indent=2, default=str))
    
    print("\nCurrent Emergency Reports in DB:", len(EMERGENCY_REPORTS_DB))
    print("Current Epidemic Reports in DB:", len(EPIDEMIC_TRACKING_DB))