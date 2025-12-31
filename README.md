# LlamaIndex_FastAPI_AI_Agent_Simple
Simple AI Agent Backend using Llamaindex and FastAPI

Features
- Azure OpenAI GPT-4 integration
- Conversation history stored in Postgres database (Supabase)
- API key authentication
- Multiple chat threads support

## Usage Instructions
Install python packages
```
pip install -r requirements.txt
```

Configure environment variables
```
cp .env.example .env
```


```
API_KEY: Create your own secret key for API authentication

AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL
AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
AZURE_OPENAI_DEPLOYMENT: Your deployment name (e.g., "gpt-4o")
AZURE_OPENAI_API_VERSION: API version (default: "2024-05-01-preview")

POSTGRES_CONNECTION_STRING: Your Postgres Conection String
```

Define the Postgres Table to use in `main.py`. Llamaindex will automatically create the table for us in Postgres. 
```
chat_store = PostgresChatStore.from_uri(
    uri=POSTGRES_CONNECTION_STRING,
    table_name="llamaindex_simple_chat_history"
)
```

Run the application
```
python main.py
```

Run using uvicorn
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Testing
Install pytest
```
pip install pytest
```

Run the testing script
```
pytest test_api.py -v -s
```

## API Endpoints

All endpoints (except `/`) require the `X-API-Key` header with your API key.

### 1. Health Check
```
GET /
```
No authentication required.

### 2. Send Chat Message
```
POST /chat
```

**Headers:**
```
X-API-Key: your-secret-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "thread_id": "user123",
  "message": "Hello! How are you?",
  "system_prompt": "You are a helpful AI assistant."
}
```

**Response:**
```json
{
  "thread_id": "user123",
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?"
}
```

### 3. Get Thread History
```
GET /threads/{thread_id}
```

**Response:**
```json
{
  "thread_id": "user123",
  "message_count": 4,
  "messages": [
    {
      "role": "user",
      "content": "Hello!"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?"
    }
  ]
}
```

### 4. List All Threads
```
GET /threads
```

**Response:**
```json
{
  "thread_count": 2,
  "threads": [
    {
      "thread_id": "user123",
      "message_count": 4
    },
    {
      "thread_id": "user456",
      "message_count": 2
    }
  ]
}
```

### 5. Delete Thread
```
DELETE /threads/{thread_id}
```

**Response:**
```json
{
  "message": "Thread user123 deleted successfully"
}
```

## Example Usage with cURL

**Send a chat message:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "user123",
    "message": "What is Python?",
    "system_prompt": "You are a helpful programming tutor."
  }'
```

**Get thread history:**
```bash
curl http://localhost:8000/threads/user123 \
  -H "X-API-Key: your-secret-api-key"
```

## Example Usage with Python

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "your-secret-api-key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Send a message
response = requests.post(
    f"{API_URL}/chat",
    headers=headers,
    json={
        "thread_id": "user123",
        "message": "Tell me a joke",
        "system_prompt": "You are a funny comedian."
    }
)

print(response.json())
```

## Project Structure

```
.
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── .env.example        # Example environment variables
├── .env                # Your environment variables (create this)
└── README.md           # This file
```

## Key Concepts

### Thread ID
- A unique identifier for each conversation
- Use the same `thread_id` to continue a conversation
- Different `thread_id` values create separate conversations
- Can be a user ID, session ID, or any unique string

### Chat History
- Automatically stored in Supabase PostgreSQL
- Retrieved on each request to maintain context
- Token limit of 3000 to prevent exceeding API limits

### API Key Authentication
- Simple header-based authentication
- Add `X-API-Key` header to all requests (except health check)
- Change the API key in your `.env` file

