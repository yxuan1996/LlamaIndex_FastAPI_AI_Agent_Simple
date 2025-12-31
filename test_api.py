import os
import pytest
import requests
import uuid
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()

# 2. Configuration
# We use the same logic as your app to get the key, ensuring they match
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
BASE_URL = "http://0.0.0.0:8000"  # Adjust if your app runs elsewhere

# 3. Request Headers with Authentication
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def unique_thread_id():
    """Generates a unique thread ID for this test run to avoid collisions."""
    return f"test_thread_{uuid.uuid4()}"

# ============================================================================
# TESTS
# ============================================================================

def test_health_check():
    """Verify the API is running and accessible."""
    url = f"{BASE_URL}/"
    # Note: Health check doesn't require auth in your code, but checking if it's public
    response = requests.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] == "AI Agent API"

def test_unauthorized_access():
    """Verify that endpoints are protected against invalid API keys."""
    url = f"{BASE_URL}/threads"
    bad_headers = {"x-api-key": "wrong-key"}
    response = requests.get(url, headers=bad_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API Key"

def test_chat_flow(unique_thread_id):
    """
    Test the full chat lifecycle:
    1. Send a message (POST /chat)
    2. Retrieve history (GET /threads/{id})
    3. List threads (GET /threads)
    4. Delete thread (DELETE /threads/{id})
    """
    
    # --- Step 1: Send a Message ---
    print(f"\n[Testing] Sending chat to thread: {unique_thread_id}")
    chat_payload = {
        "thread_id": unique_thread_id,
        "message": "Hello, this is a test message.",
        "system_prompt": "You are a concise testing assistant."
    }
    
    chat_response = requests.post(f"{BASE_URL}/chat", json=chat_payload, headers=HEADERS)
    
    # If the LLM/DB isn't actually running, this might fail with 500. 
    # We assert 200 assuming the environment is set up correctly.
    assert chat_response.status_code == 200, f"Chat failed: {chat_response.text}"
    chat_data = chat_response.json()
    assert chat_data["thread_id"] == unique_thread_id
    assert "response" in chat_data
    assert len(chat_data["response"]) > 0

    # --- Step 2: Get Thread History ---
    print(f"[Testing] Retrieving history for: {unique_thread_id}")
    history_response = requests.get(f"{BASE_URL}/threads/{unique_thread_id}", headers=HEADERS)
    assert history_response.status_code == 200
    history_data = history_response.json()
    
    assert history_data["thread_id"] == unique_thread_id
    # Should have at least 2 messages: User + Assistant
    assert history_data["message_count"] >= 2 
    # Verify the user's message is in the history
    assert any(msg["content"] == "Hello, this is a test message." for msg in history_data["messages"])

    # --- Step 3: List Threads ---
    print("[Testing] Listing all threads")
    list_response = requests.get(f"{BASE_URL}/threads", headers=HEADERS)
    assert list_response.status_code == 200
    list_data = list_response.json()
    
    # Verify our test thread exists in the list
    thread_ids = [t["thread_id"] for t in list_data["threads"]]
    assert unique_thread_id in thread_ids

    # --- Step 4: Delete Thread ---
    print(f"[Testing] Deleting thread: {unique_thread_id}")
    delete_response = requests.delete(f"{BASE_URL}/threads/{unique_thread_id}", headers=HEADERS)
    assert delete_response.status_code == 200
    
    # Verify it's actually gone (fetching history should return empty or 404/empty list depending on store implementation)
    # The PostgresChatStore usually returns empty list if key doesn't exist, it doesn't raise 404
    check_response = requests.get(f"{BASE_URL}/threads/{unique_thread_id}", headers=HEADERS)
    check_data = check_response.json()
    assert check_data["message_count"] == 0

