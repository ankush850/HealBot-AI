#!/usr/bin/env python3
"""
Emergency System Simulation Runner
Run this script to test outbreak and disaster simulations
"""

import os
import sys
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for simulation runs"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'simulation_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )

def run_outbreak_simulation():
    """Run disease outbreak simulation"""
    print("\n" + "="*60)
    print("🦠 DISEASE OUTBREAK SIMULATION")
    print("="*60)
    
    try:
        from emergency_agent import emergency_system
        
        print("Running outbreak simulation...")
        results = emergency_system.run_simulation("outbreak")
        
        print(f"\n📊 SIMULATION RESULTS:")
        print(f"• Processed {len(results)} outbreak reports")
        
        # Check for alerts generated
        alerts_generated = [r for r in results if r.get('generated_alert')]
        
        if alerts_generated:
            print(f"• Alert triggered after {len(results)} reports")
            alert = alerts_generated[0]['generated_alert']
            print(f"• Alert Type: {alert['title']}")
            print(f"• Alert Level: {alert['alert_level']}")
            print(f"• Summary: {alert['summary']}")
            
            # Display the full alert
            print(f"\n🚨 GENERATED ALERT:")
            print("-" * 40)
            from emergency_agent import format_alert_for_display
            formatted_alert = format_alert_for_display(alert)
            print(formatted_alert)
            
        else:
            print("• No alerts generated (threshold not met)")
            
        return results
        
    except ImportError as e:
        print(f"❌ Error: Cannot import emergency system: {e}")
        print("Make sure emergency_agent.py is in the current directory")
        return None
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_disaster_simulation():
    """Run natural disaster simulation"""
    print("\n" + "="*60)
    print("🌊 NATURAL DISASTER SIMULATION")
    print("="*60)
    
    try:
        from emergency_agent import emergency_system
        
        print("Running disaster simulation...")
        results = emergency_system.run_simulation("disaster")
        
        print(f"\n📊 SIMULATION RESULTS:")
        print(f"• Processed {len(results)} disaster reports")
        
        # Check for alerts generated
        alerts_generated = [r for r in results if r.get('generated_alert')]
        
        if alerts_generated:
            print(f"• Alert triggered after {len(results)} reports")
            alert = alerts_generated[0]['generated_alert']
            print(f"• Alert Type: {alert['title']}")
            print(f"• Alert Level: {alert['alert_level']}")
            print(f"• Summary: {alert['summary']}")
            
            # Display the full alert
            print(f"\n🚨 GENERATED ALERT:")
            print("-" * 40)
            from emergency_agent import format_alert_for_display
            formatted_alert = format_alert_for_display(alert)
            print(formatted_alert)
            
        else:
            print("• No alerts generated (threshold not met)")
            
        return results
        
    except ImportError as e:
        print(f"❌ Error: Cannot import emergency system: {e}")
        return None
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_active_alerts():
    """Check for currently active alerts"""
    print("\n" + "="*60)
    print("📢 CURRENT ACTIVE ALERTS")
    print("="*60)
    
    try:
        from emergency_agent import emergency_system
        
        current_alerts = emergency_system.get_current_alerts()
        
        if current_alerts:
            print(f"Found {len(current_alerts)} active alerts:")
            print()
            
            for i, alert in enumerate(current_alerts, 1):
                print(f"Alert {i}:")
                print(alert)
                print("-" * 40)
                
        else:
            print("✅ No active alerts currently")
            
        return current_alerts
        
    except ImportError as e:
        print(f"❌ Error: Cannot import emergency system: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to check alerts: {e}")
        return None

def test_individual_emergency():
    """Test individual emergency report"""
    print("\n" + "="*60)
    print("🏥 INDIVIDUAL EMERGENCY TEST")
    print("="*60)
    
    try:
        from emergency_agent import emergency_system
        
        # Test with a query that should trigger health concern but not outbreak
        test_query = "I have severe chest pain and difficulty breathing"
        
        print(f"Testing individual emergency: {test_query}")
        result = emergency_system.process_emergency_report(test_query)
        
        print("\n📋 INDIVIDUAL EMERGENCY RESPONSE:")
        print("-" * 40)
        print(result['emergency_response'])
        
        if result.get('generated_alert'):
            print("\n⚠️  This individual report also triggered a public alert!")
            print("(This usually means there are other similar reports)")
            
        return result
        
    except ImportError as e:
        print(f"❌ Error: Cannot import emergency system: {e}")
        return None
    except Exception as e:
        print(f"❌ Individual test failed: {e}")
        return None

def run_custom_simulation():
    """Allow user to input custom emergency scenarios"""
    print("\n" + "="*60)
    print("🎭 CUSTOM EMERGENCY SIMULATION")
    print("="*60)
    
    try:
        from emergency_agent import emergency_system
        
        print("Enter emergency scenarios to test (type 'done' to finish):")
        print("Examples:")
        print("  - High fever and cough, many people in area sick")
        print("  - Severe flooding in our neighborhood")
        print("  - Building collapsed in earthquake")
        print()
        
        scenarios = []
        while True:
            scenario = input("Enter emergency scenario: ").strip()
            if scenario.lower() == 'done' or not scenario:
                break
            scenarios.append(scenario)
        
        if not scenarios:
            print("No scenarios entered.")
            return None
        
        print(f"\nProcessing {len(scenarios)} custom scenarios...")
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n--- Scenario {i}: {scenario[:50]}... ---")
            result = emergency_system.process_emergency_report(scenario)
            results.append(result)
            
            print(f"Emergency Type: {result.get('emergency_type', 'Unknown')}")
            print(f"Vulnerability: {result.get('vulnerability_level', 'Unknown')}")
            
            if result.get('generated_alert'):
                print("🚨 PUBLIC ALERT GENERATED!")
                break
        
        # Show final summary
        print(f"\n📊 CUSTOM SIMULATION SUMMARY:")
        print(f"• Processed {len(results)} scenarios")
        alerts = [r for r in results if r.get('generated_alert')]
        if alerts:
            print(f"• Generated {len(alerts)} public alerts")
        
        return results
        
    except ImportError as e:
        print(f"❌ Error: Cannot import emergency system: {e}")
        return None
    except Exception as e:
        print(f"❌ Custom simulation failed: {e}")
        return None

def main():
    """Main simulation runner"""
    setup_logging()
    
    print("🚨 EMERGENCY SYSTEM SIMULATION RUNNER 🚨")
    print("="*60)
    print("This script will test the emergency alert generation system.")
    print("Choose what to run:")
    print()
    print("1. Disease Outbreak Simulation")
    print("2. Natural Disaster Simulation") 
    print("3. Check Active Alerts")
    print("4. Test Individual Emergency")
    print("5. Custom Emergency Scenarios")
    print("6. Run All Simulations")
    print("7. Exit")
    print()
    
    while True:
        try:
            choice = input("Select option (1-7): ").strip()
            
            if choice == '1':
                run_outbreak_simulation()
                
            elif choice == '2':
                run_disaster_simulation()
                
            elif choice == '3':
                check_active_alerts()
                
            elif choice == '4':
                test_individual_emergency()
                
            elif choice == '5':
                run_custom_simulation()
                
            elif choice == '6':
                print("\n🔄 RUNNING ALL SIMULATIONS...")
                run_outbreak_simulation()
                run_disaster_simulation()
                check_active_alerts()
                test_individual_emergency()
                
            elif choice == '7':
                print("\n👋 Simulation runner exiting...")
                break
                
            else:
                print("Invalid choice. Please select 1-7.")
                continue
            
            print("\n" + "="*60)
            print("Simulation complete. Choose another option or exit.")
            
        except KeyboardInterrupt:
            print("\n\n👋 Exiting simulation runner...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    main()