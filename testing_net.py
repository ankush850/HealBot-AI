# test_connection.py
import requests

def test_api_endpoints():
    base_url = "http://127.0.0.1:8000"
    
    endpoints_to_test = [
        "/health",
        "/status", 
        "/alerts/current",
        "/simulation/status"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"✅ {endpoint}: {response.status_code}")
            if endpoint == "/alerts/current":
                data = response.json()
                print(f"   Alerts: {data.get('count', 0)}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

if __name__ == "__main__":
    test_api_endpoints()