import datetime
import uuid
from fastapi import HTTPException
from tools import call_tools
from translation import translate_text
from config import config as config
from functions import generate_session_name, chunk_text
import asyncio, time
import json
from pymongo.collection import Collection
from typing import AsyncGenerator


# timezone = config['TIMEZONE']['TZ']
# tz = pytz.timezone(timezone)


def create_session_if_not_exists(collection, emp_id):
    """
    Creates a new session for the employee if one does not already exist.

    Args:
    - collection (MongoDB collection): MongoDB collection object.
    - emp_id (str): Employee ID for whom the session is being created.

    Raises:
    - HTTPException 404: If session creation fails or employee ID is not found in the collection.
    """
    try:
        if not collection.find_one({'emp_id': emp_id}):
            collection.insert_one({'emp_id': emp_id, 'sessions': []})
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to create session: {str(e)}")



def get_all_sessions(collection, emp_id):
    """
    Retrieves all sessions associated with the employee ID from the collection.

    Args:
    - collection (MongoDB collection): MongoDB collection object.
    - emp_id (str): Employee ID for whom sessions are being retrieved.

    Returns:
    - list: List of dictionaries containing session details.

    Raises:
    - HTTPException 404: If no sessions are found for the specified employee ID.
    """
    try:
        employee = collection.find_one({'emp_id': emp_id}, {'sessions': 1})
        
        if employee and 'sessions' in employee:
            sessions = []
            for session in employee['sessions']:
                session_id = session['session_id']
                session_name = session.get('session_name', '')
                
                # Extract the most recent timestamp from the session messages
                if 'messages' in session and session['messages']:
                    most_recent_message = max(session['messages'], key=lambda msg: msg['timestamp'])
                    most_recent_timestamp = most_recent_message['timestamp']
                else:
                    most_recent_timestamp = None
                
                sessions.append({'session_id': session_id, 'session_name': session_name, 'most_recent_timestamp': most_recent_timestamp})
            
            # Sort sessions by most recent timestamp in descending order
            sessions.sort(key=lambda x: x['most_recent_timestamp'], reverse=True)
            
            # Remove the 'most_recent_timestamp' from the output
            for session in sessions:
                session.pop('most_recent_timestamp')
            
            return sessions
        else:
            raise HTTPException(status_code=404, detail="No sessions found for this employee")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to retrieve sessions: {str(e)}")

   

def handle_query_logic(collection, emp_id, query, session_id=None):
    """
    Handles the logic for processing user queries within a session.

    Args:
    - collection (MongoDB collection): MongoDB collection object.
    - emp_id (str): Employee ID for whom the query is being processed.
    - query (str): User query to be processed.
    - session_id (str, optional): Session ID where the query should be processed. Defaults to None.

    Returns:
    - dict: Response containing the status, translated response, and session ID.

    Raises:
    - HTTPException 404: If session or token data is not found, or if there are issues with API calls.
    """
    try:
        token_data = collection.find_one({'emp_id': emp_id})
        print("1")
        if not token_data:
            raise HTTPException(status_code=404, detail="Token not found")
        print("2")
        if session_id:
            print("3")
            session = next((s for s in token_data['sessions'] if s['session_id'] == session_id), None)
            print("4")
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            print("5")
            session_id = str(uuid.uuid4())
            print("6")
            session_name = generate_session_name(query)
            print("7")
            new_session = {'session_id': session_id, 'session_name': session_name, 'messages': []}
            print("8")
            collection.update_one(
                {'emp_id': emp_id},
                {'$push': {'sessions': new_session}}
            )
            print("9")
            session = new_session

        # translated_query_response = translate_text(query, 'en')
        # detected_language = translated_query_response[0]['detectedLanguage']['language']
        # translated_query = translated_query_response[0]['translations'][0]['text']
        print("10")
        message = {
            'role': 'user',
            'content': query,
            'timestamp': datetime.datetime.now().isoformat()
        }
        print("11")
        collection.update_one(
            {'emp_id': emp_id, 'sessions.session_id': session_id},
            {'$push': {'sessions.$.messages': message}}
        )
        print("12")
        final_response = call_tools(query, emp_id, session_id)
        print("13")
        # if detected_language.lower() == 'en':
        #     translated_response = final_response
        # else:
        #     translated_response = translate_text(final_response, detected_language)[0]['translations'][0]['text']

        print("14")
        message = {
            'role': 'ai',
            'content': final_response,
            'timestamp': datetime.datetime.now().isoformat()
        }
        collection.update_one(
            {'emp_id': emp_id, 'sessions.session_id': session_id},
            {'$push': {'sessions.$.messages': message}}
        )
        
        return {"status": "success", "response": final_response, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to handle query: {str(e)}")


# chunck by line
def chunk_text(text: str, by_line: bool = True, chunk_size: int = 1):
    """Chunk text into lines if by_line is True, otherwise split into words."""
    if by_line:
        lines = text.split('\n')
        for line in lines:
            yield line
    else:
        words = text.split()
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i:i + chunk_size])


# async def generate_response_stream(query: str, emp_id: str, collection: Collection, session_id: str = None) -> AsyncGenerator[str, None]:
#     """
#     Generate response in chunks to support streaming.
#     """
#     try:
#         # Retrieve token data
#         token_data = collection.find_one({'emp_id': emp_id})
#         if not token_data:
#             raise HTTPException(status_code=404, detail="Token not found")
        
#         # Handle session
        
#         session = next((s for s in token_data['sessions'] if s['session_id'] == session_id), None)
        
#         if not session:
#             # session_id = str(uuid.uuid4())
#             session_name = generate_session_name(query)
#             new_session = {'session_id': session_id, 'session_name': session_name, 'messages': []}
#             collection.update_one(
#                 {'emp_id': emp_id},
#                 {'$push': {'sessions': new_session}}
#             )
#             session = new_session

#         # Log user message
#         message = {
#             'role': 'user',
#             'content': query,
#             'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat()
#         }
#         collection.update_one(
#             {'emp_id': emp_id, 'sessions.session_id': session_id},
#             {'$push': {'sessions.$.messages': message}}
#         )

#         # Generate final response
#         final_response = call_tools(query, emp_id, session_id)
#         # print(final_response)

#         # Decide chunking strategy based on presence of new lines
#         by_line = '\n' in final_response

#         # Initialize full response string
#         full_response = ""

#         # Use chunk_text function based on by_line flag
#         chunks = chunk_text(final_response, by_line=by_line, chunk_size=1)

#         # Stream and store each chunk
#         if (by_line == True):
#             for chunk in chunks:
#                 full_response += chunk + "\n"  # Concatenate chunk to full response
#                 yield chunk + "\n"  # Stream the chunk
#                 await asyncio.sleep(0.1)  # Simulate delay

#         else:
#             for chunk in chunks:
#                 chunk = chunk.strip()
#                 full_response += chunk + " "
#                 yield chunk + " "
#                 await asyncio.sleep(0.1)

#             # Store each chunk in MongoDB
#             # collection.update_one(
#             #     {'emp_id': emp_id, 'sessions.session_id': session_id},
#             #     {'$push': {'sessions.$.messages': {
#             #         'role': 'ai',
#             #         'content': chunk,
#             #         'timestamp': datetime.datetime.now().isoformat()
#             #     }}}
#             # )

#         # Store the final combined response in MongoDB
#         ai_message = {
#             "role": "ai",
#             "content": full_response.strip(),
#             "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
#         }
#         collection.update_one(
#             {'emp_id': emp_id, 'sessions.session_id': session_id},
#             {'$push': {'sessions.$.messages': ai_message}}
#         )
        
#     except Exception as e:
#         yield "An error occurred. Please try rephrasing your question or ask something else."
#         print(f"Error: {e}")

# # Generator function to convert generator to list if needed
# def generator_to_list(generator):
#     return list(generator)

def get_session_by_id(collection, emp_id, session_id):
    """
    Retrieves a session's details by its session ID.

    Args:
    - collection (MongoDB collection): MongoDB collection object.
    - emp_id (str): Employee ID for whom the session details are being retrieved.
    - session_id (str): Session ID of the session to retrieve.

    Returns:
    - dict: Dictionary containing session details.

    Raises:
    - HTTPException 404: If session details are not found for the specified session ID.
    """
    try:
        session = collection.find_one({'emp_id': emp_id, 'sessions.session_id': session_id}, {'sessions.$': 1})

        if session and session.get('sessions'):
            session_data = session['sessions'][0]
            session_data['messages'] = [
                {
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp']
                }
                for msg in session_data.get('messages', [])
            ]
            return session_data
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to retrieve session: {str(e)}")





def delete_session_by_id(collection, emp_id, session_id):
    """
    Deletes a session by its session ID.

    Args:
    - collection (MongoDB collection): MongoDB collection object.
    - emp_id (str): Employee ID for whom the session is being deleted.
    - session_id (str): Session ID of the session to delete.

    Returns:
    - dict: Response indicating the status of the operation.

    Raises:
    - HTTPException 404: If session deletion fails or session ID is not found.
    """
    try:
        result = collection.update_one(
            {'emp_id': emp_id},
            {'$pull': {'sessions': {'session_id': session_id}}}
        )
        if result.modified_count == 1:
            return {"status": "success", "message": f"Session with session_id '{session_id}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Session with session_id '{session_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to delete session: {str(e)}")




def update_session_name_by_id(collection, emp_id, session_id, new_name):
    """
    Updates a session's name by its session ID.

    Args:
    - collection (MongoDB collection): MongoDB collection object.
    - emp_id (str): Employee ID for whom the session name is being updated.
    - session_id (str): Session ID of the session whose name is to be updated.
    - new_name (str): New name to assign to the session.

    Returns:
    - dict: Response indicating the status of the operation.

    Raises:
    - HTTPException 404: If session name update fails or session ID is not found.
    """
    try:
        result = collection.update_one(
            {'emp_id': emp_id, 'sessions.session_id': session_id},
            {'$set': {'sessions.$.session_name': new_name}}
        )

        if result.modified_count == 1:
            return {"status": "success", "message": f"Session name updated successfully for session_id '{session_id}'"}
        else:
            raise HTTPException(status_code=404, detail=f"Session with session_id '{session_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to update session name: {str(e)}")