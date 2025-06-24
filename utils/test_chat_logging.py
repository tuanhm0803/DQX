"""
Test script for chat logging functionality
"""
import requests
import json

def test_chat_logging():
    """Test the chat logging endpoint"""
    url = "http://127.0.0.1:8000/api/log_chat"
    
    payload = {
        "user_message": "This is a test message from the user",
        "assistant_response": "This is a test response from the assistant"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat_logging()
