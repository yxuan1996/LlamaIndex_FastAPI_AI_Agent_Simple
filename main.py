from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.storage.chat_store.postgres import PostgresChatStore

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="AI Agent API", version="1.0.0")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Key for securing endpoints (from .env file)
VALID_API_KEY = os.getenv("API_KEY", "your-secret-api-key")

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Supabase PostgreSQL Configuration
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")

# ============================================================================
# INITIALIZE COMPONENTS
# ============================================================================

# Initialize Azure OpenAI LLM
llm = AzureOpenAI(
    engine=AZURE_OPENAI_DEPLOYMENT,
    model="gpt-4o",
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

# Initialize PostgreSQL Chat Store for conversation history
chat_store = PostgresChatStore.from_uri(
    uri=POSTGRES_CONNECTION_STRING,
    table_name="llamaindex_simple_chat_history"
)

# ============================================================================
# SECURITY: API KEY AUTHENTICATION
# ============================================================================

def verify_api_key(x_api_key: str = Header(...)):
    """
    Verify that the API key in the request header matches our valid key.
    This dependency is used to protect endpoints.
    """
    if x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for sending a message to the AI agent"""
    thread_id: str  # Unique identifier for the conversation thread
    message: str    # User's message
    system_prompt: Optional[str] = "You are a helpful AI assistant."

class ChatResponse(BaseModel):
    """Response model containing the AI agent's reply"""
    thread_id: str
    response: str

class ThreadInfo(BaseModel):
    """Information about a chat thread"""
    thread_id: str
    message_count: int

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "AI Agent API",
        "version": "1.0.0"
    }

@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent and get a response.
    
    This endpoint:
    1. Retrieves conversation history for the thread
    2. Adds the user's message to history
    3. Generates a response using Azure OpenAI
    4. Saves both messages to the database
    5. Returns the AI's response
    """
    try:
        # Retrieve existing conversation history for this thread
        chat_history = chat_store.get_messages(key=request.thread_id)
        
        # Create a memory buffer with the conversation history
        memory = ChatMemoryBuffer.from_defaults(
            chat_history=chat_history,
            token_limit=3000  # Limit context to prevent exceeding token limits
        )
        
        # Add user message to memory
        user_message = ChatMessage(role="user", content=request.message)
        memory.put(user_message)
        
        # Prepare messages for the LLM (system prompt + conversation history)
        messages = [
            ChatMessage(role="system", content=request.system_prompt)
        ] + memory.get()
        
        # Get response from Azure OpenAI
        response = llm.chat(messages)
        assistant_message = ChatMessage(role="assistant", content=str(response))
        
        # Save both user and assistant messages to the database
        memory.put(assistant_message)
        chat_store.set_messages(key=request.thread_id, messages=memory.get())
        
        return ChatResponse(
            thread_id=request.thread_id,
            response=str(response)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/threads/{thread_id}", dependencies=[Depends(verify_api_key)])
async def get_thread_history(thread_id: str):
    """
    Retrieve the complete conversation history for a specific thread.
    Returns all messages in chronological order.
    """
    try:
        messages = chat_store.get_messages(key=thread_id)
        
        # Format messages for easy reading
        formatted_messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
        
        return {
            "thread_id": thread_id,
            "message_count": len(formatted_messages),
            "messages": formatted_messages
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving thread: {str(e)}")

@app.delete("/threads/{thread_id}", dependencies=[Depends(verify_api_key)])
async def delete_thread(thread_id: str):
    """
    Delete all conversation history for a specific thread.
    Useful for clearing old conversations or resetting a thread.
    """
    try:
        chat_store.delete_messages(key=thread_id)
        return {
            "message": f"Thread {thread_id} deleted successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting thread: {str(e)}")

@app.get("/threads", dependencies=[Depends(verify_api_key)])
async def list_threads():
    """
    List all available chat threads.
    Returns thread IDs and their message counts.
    """
    try:
        keys = chat_store.get_keys()
        
        threads = []
        for key in keys:
            messages = chat_store.get_messages(key=key)
            threads.append({
                "thread_id": key,
                "message_count": len(messages)
            })
        
        return {
            "thread_count": len(threads),
            "threads": threads
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing threads: {str(e)}")

# ============================================================================
# RUN THE APPLICATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)