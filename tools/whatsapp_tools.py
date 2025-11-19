# Send free text message via WhatsApp Cloud API
def send_whatsapp_text(recipient_number, message_text, api_key=None):
    """
    Send a free text message to a WhatsApp user using the WhatsApp Cloud API.
    Args:
        recipient_number (str): WhatsApp number to send to (e.g., '919148033536').
        message_text (str): The message text to send.
        api_key (str, optional): WhatsApp API key. If not provided, will use WHATSAPP_API_KEY from .env.
    Returns:
        dict: JSON response from the WhatsApp API.
    """
    if api_key is None:
        api_key = os.getenv("WHATSAPP_API_KEY")
    if not api_key:
        return {"error": "No WhatsApp API key provided or found in environment."}
    url = "https://graph.facebook.com/v22.0/726446113895256/messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {"body": message_text}
    }
    response = requests.post(url, headers=headers, json=payload)
    try:
        return response.json()
    except Exception:
        return {"error": "Invalid response", "status_code": response.status_code, "text": response.text}
import requests
import os
from dotenv import load_dotenv
load_dotenv()

def send_whatsapp_template(recipient_number, template_name="hello_world", language_code="en_US", api_key=None):
    """
    Send a WhatsApp template message using the Facebook Graph API.
    Args:
        recipient_number (str): WhatsApp number to send to (e.g., '919148033536').
        template_name (str): Name of the WhatsApp template (default: 'hello_world').
        language_code (str): Language code for the template (default: 'en_US').
        api_key (str, optional): WhatsApp API key. If not provided, will use WHATSAPP_API_KEY from .env.
    Returns:
        dict: JSON response from the WhatsApp API.
    """
    if api_key is None:
        api_key = os.getenv("WHATSAPP_API_KEY")
    if not api_key:
        return {"error": "No WhatsApp API key provided or found in environment."}
    url = "https://graph.facebook.com/v22.0/726446113895256/messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code}
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    try:
        return response.json()
    except Exception:
        return {"error": "Invalid response", "status_code": response.status_code, "text": response.text}

# Example usage (uncomment to test):
# result = send_whatsapp_template("919148033536")
# print(result)

# [2025-09-29] feat(agent): add differential diagnosis inference engine

# [2025-10-04] docs: add comprehensive README with architecture and setup guide

# [2025-10-08] perf(vector): optimize index search query latency

# [2025-10-12] feat(booking): format confirmation message with doctor details and time

# [2025-10-16] fix(booking): fix date formatting for upcoming appointment notifications

# [2025-10-21] feat(dashboard): add interactive Plotly charts for triage trends

# [2025-10-25] feat(agent): improve hallucination guards in medical responses

# [2025-10-29] docs: add troubleshooting guide for local deployment

# [2025-11-02] perf(db): optimize SQLite PRAGMA settings for read-heavy workloads

# [2025-11-07] feat(booking): add automated reminder notifications before appointments

# [2025-11-11] feat(emergency): generate summary report PDF export hook

# [2025-11-15] refactor(api): use typed dependency injection for service instances

# [2025-11-20] feat(booking): add doctor specialty auto-recommendation based on symptoms
