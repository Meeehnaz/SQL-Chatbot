from fastapi import HTTPException, APIRouter, Body, Request
from fastapi.responses import StreamingResponse
from database.__init__ import get_conn, conn_mongodb
from functions import create_agent, employee_ID, llm
from session_operations import (
    create_session_if_not_exists,
    get_all_sessions,
    handle_query_logic,
    get_session_by_id,
    delete_session_by_id,
    update_session_name_by_id,
    # generate_response_stream
)
from config import config as config
import asyncio, json
from typing import AsyncGenerator


router = APIRouter()

# local storage for token and employee ID
token_storage = {}
emp_id_storage = {}

db = get_conn() # connect to database
agent = create_agent(db, llm) # create database agent
collection = conn_mongodb() # connect to mongoDB



@router.get("/sessions", tags=["Chatbot"])
async def get_all_sessions_endpoint(token: str):
    """
    Endpoint to retrieve all sessions associated with the provided token.

    Args:
    - token (str): Employee token for authentication.

    Returns:
    - dict: Dictionary containing the status and sessions retrieved.
    """

    emp_id = employee_ID(db, token)
    emp_id_storage['emp_id'] = emp_id
    token_storage['token_storage'] = token
    
    create_session_if_not_exists(collection, emp_id)
    
    sessions = get_all_sessions(collection, emp_id)
    return {"status": "success", "sessions": sessions}


@router.post("/chatbot")
async def handle_query_endpoint(query: str , session_id: str = None):
    """
    Endpoint to handle user queries and interact with the chatbot.

    Args:
    - query (str): User query to be processed.
    - session_id (str, optional): Session ID for context, if provided.

    Returns:
    - dict: Dictionary containing the status, response, and session ID.

    """

    emp_id = emp_id_storage.get('emp_id')
    
    response = handle_query_logic(collection, emp_id, query, session_id)

    return response

# @router.post("/chatbot")
# async def handle_query_endpoint(query: str, session_id: str):
#     """
#     Endpoint to handle user queries and interact with the chatbot.

#     Args:
#     - query (str): User query to be processed.
#     - session_id (str, optional): Session ID for context, if provided.

#     Returns:
#     - StreamingResponse: Streamed response from the chatbot.
#     """

#     emp_id = emp_id_storage.get('emp_id')
    
#     async def stream_and_store() -> AsyncGenerator[str, None]:
#         # ai_response = ""
#         async for chunk in generate_response_stream(query, emp_id, collection, session_id):
#             # ai_response += chunk
#             # print(chunk)  # Print each chunk to the terminal
#             yield chunk
        
#     return StreamingResponse(stream_and_store(), media_type="text/plain")
    
 



@router.get("/session/{session_id}")
async def get_session_endpoint(session_id: str):
    """
    Endpoint to retrieve session details by session ID.

    Args:
    - session_id (str): Session ID to retrieve details for.

    Returns:
    - dict: Dictionary containing session details.

    """
   
    emp_id = emp_id_storage.get('emp_id')
    session_data = get_session_by_id(collection, emp_id, session_id)
    return session_data
    


@router.delete("/session/{session_id}")
async def delete_session_endpoint(session_id: str):
    """
    Endpoint to delete a session by session ID.

    Args:
    - session_id (str): Session ID to delete.

    Returns:
    - dict: Dictionary containing status message.
    """

    emp_id = emp_id_storage.get('emp_id')
    response = delete_session_by_id(collection, emp_id, session_id)
    return response
   


@router.put("/session/{session_id}/update-name")
async def update_session_name_endpoint(session_id: str, new_name: str = Body(...)):
    """
    Endpoint to update session name by session ID.

    Args:
    - session_id (str): Session ID to update.
    - new_name (str): New name for the session.

    Returns:
    - dict: Dictionary containing status message.

    """

    emp_id = emp_id_storage.get('emp_id')
    response = update_session_name_by_id(collection, emp_id, session_id, new_name)
    return response