# test_fixed.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_emergency_system():
    print("Testing emergency system with fixes...")
    
    try:
        from agents.emergency_agent import emergency_system
        print("✓ Emergency system imported")
        
        # Test with simple reports that should trigger alert
        test_queries = [
            "High fever and cough, many people sick in my area",
            "Fever headache body ache, neighbors also have fever",
            "Persistent fever and cough, outbreak suspected"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nProcessing report {i}: {query}")
            result = emergency_system.process_emergency_report(query)
            
            print(f"- Status: {result.get('status', 'unknown')}")
            print(f"- Emergency type: {result.get('emergency_type', 'None')}")
            print(f"- Alert generated: {result.get('generated_alert') is not None}")
            
            if result.get('generated_alert'):
                print(f"🚨 ALERT: {result['generated_alert'].get('title', 'Unknown')}")
                break
        
        # Check alerts
        alerts = emergency_system.get_current_alerts()
        print(f"\nFinal alerts: {len(alerts)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_emergency_system()