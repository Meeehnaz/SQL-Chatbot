import io, os
import numpy as np
from io import BytesIO
import requests, faiss
from openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentType
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from sqlalchemy.orm import sessionmaker
from langchain_core.prompts import ChatPromptTemplate
from azure.storage.blob import BlobServiceClient
from fastapi import HTTPException
from config import config as config
from schema import get_schema
from prompt import get_prompt, get_suffix, get_followup_prompt
from operator import itemgetter
from database.__init__ import get_conn
import asyncio


# Initialize Blob service client
storage_string = config["BLOB-STORAGE-STRING"]["STRING"]
blob_service_client = BlobServiceClient.from_connection_string(storage_string)

# Initialize Azure OpenAI clients
api_key = config["AZURE"]["AZURE_API_KEY"]
azure_endpoint = config["AZURE"]["AZURE_OPENAI_ENDPOINT"]
azure_version = config["AZURE"]["API_VERSION"]
deployment = config["AZURE"]["DEPLOYMENT2"]

# Language Model for generating responses
llm = AzureChatOpenAI(
    api_key=api_key,
    api_version=azure_version,
    azure_endpoint=azure_endpoint,
    azure_deployment=deployment
)

# OpenAI Embeddings Client
client = AzureOpenAI(
  api_key = api_key,  
  api_version = azure_version,
  azure_endpoint = azure_endpoint
)

# connect to the Database
db_engine = get_conn()


def get_openai_embedding(text):
    """
    Generates OpenAI embeddings for a given text.

    Args:
    - text (str): Input text to generate embeddings.

    Returns:
    - np.ndarray: Numpy array representing the embeddings.

    Raises:
    - Exception: If there is an error generating the embedding.
    """
    try:
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-ada-002"
        )
        embedding = response.data[0].embedding
        return np.array(embedding)
    except Exception as e:
        raise HTTPException(f"Error generating embedding: {e}")



def load_npy_from_blob(blob_client):
    """
    Loads data from a .npy file stored in Azure Blob Storage.

    Args:
    - blob_client: Azure Blob Client object for the .npy file.

    Returns:
    - np.ndarray: Loaded numpy array from the .npy file.

    Raises:
    - Exception: If there is an error loading the .npy file from Blob Storage.
    """
    # try:
    #     blob_data = blob_client.download_blob().readall()
    #     npy_data = np.load(io.BytesIO(blob_data), allow_pickle=True)
    #     return npy_data
    # except Exception as e:
    #     raise HTTPException(f"Error loading npy file from blob: {e}")

    try:
        npy_data = np.load(blob_client, allow_pickle=True)
        return npy_data
    except Exception as e:
        raise HTTPException(f"Error loading npy file: {e}")



# def load_faiss_data_from_npy(container_name, connection_string):
#     """
#     Loads FAISS index data and embeddings from .npy files in Azure Blob Storage.

#     Args:
#     - container_name (str): Name of the Azure Blob Storage container.
#     - connection_string (str): Connection string for Azure Blob Storage.

#     Returns:
#     - dict: Dictionary containing FAISS index, embeddings, and texts.

#     Raises:
#     - Exception: If there is an error loading FAISS data from .npy files.
#     """
#     try:
#         blob_service_client = BlobServiceClient.from_connection_string(connection_string)
#         container_client = blob_service_client.get_container_client(container_name)

#         embeddings_blob_client = container_client.get_blob_client(f"UserManual_embeddings.npy")
#         texts_blob_client = container_client.get_blob_client(f"UserManual_texts.npy")
#         index_blob_client = container_client.get_blob_client(f"UserManual_index.npy")

#         embeddings = load_npy_from_blob(embeddings_blob_client)
#         texts = load_npy_from_blob(texts_blob_client)
#         index_data = load_npy_from_blob(index_blob_client)

#         # Create FAISS index and add index data
#         index = faiss.IndexFlatL2(1536)
#         index.add(index_data)

#         return {"index": index, "embeddings": embeddings, "texts": texts}
#     except Exception as e:
#         raise HTTPException(f"Error loading FAISS data from blob: {e}")

def load_faiss_data_from_npy(directory_path):
    """
    Loads FAISS index data and embeddings from .npy files stored locally.

    Args:
    - directory_path (str): Path to the directory containing the .npy files.

    Returns:
    - dict: Dictionary containing FAISS index, embeddings, and texts.

    Raises:
    - Exception: If there is an error loading FAISS data from .npy files.
    """
    try:
        directory_path = "C:/Users/mmurtuza001/chatbot new pdf/"
        embeddings_file_path = os.path.join(directory_path, "file_embeddings.npy")
        texts_file_path = os.path.join(directory_path, "file_texts.npy")
        index_file_path = os.path.join(directory_path, "file_index.npy")

        embeddings = load_npy_from_blob(embeddings_file_path)
        texts = load_npy_from_blob(texts_file_path)
        index_data = load_npy_from_blob(index_file_path)

        # Create FAISS index and add index data
        index = faiss.IndexFlatL2(1536)
        index.add(index_data)

        return {"index": index, "embeddings": embeddings, "texts": texts}
    except Exception as e:
        raise HTTPException(f"Error loading FAISS data: {e}")



def search_vector_store(index, texts, query, k=3):
    """
    Searches for vectors similar to a query in a FAISS index.

    Args:
    - index: FAISS index object.
    - texts (np.ndarray): Array of texts corresponding to the index.
    - query (str): Query text to search for.
    - k (int, optional): Number of nearest neighbors to retrieve. Defaults to 3.

    Returns:
    - list: List of texts similar to the query.

    Raises:
    - Exception: If there is an error searching the vector store.
    """
    try:
        query_embedding = get_openai_embedding(query)
        D, I = index.search(np.array([query_embedding]), k)
        results = [texts[i] for i in I[0]]
        return results
    except Exception as e:
        raise HTTPException(f"Error searching vector store: {e}")


def generate_response(question, context):
    """
    Generates a response to a question using an Azure OpenAI model.

    Args:
    - question (str): Question to generate a response for.
    - context (str): Context for the question.

    Returns:
    - str: Generated response.

    Raises:
    - Exception: If there is an error generating the response.
    """
    try:
        messages = [
            {"role": "system", "content": "You are an AI Document Q&A Chatbot, you must answer the question given by the user with respect to the context given. If a user greets you, you must greet them back politely"},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
        ]

        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=0.5,
            
        )

        answer = response.choices[0].message.content.strip()

        return answer
    except Exception as e:
        raise HTTPException(f"Error generating response: {e}")

# async def generate_response(question, context):
#     """
#     Generates a response to a question using an Azure OpenAI model in streaming mode.

#     Args:
#     - question (str): Question to generate a response for.
#     - context (str): Context for the question.

#     Yields:
#     - str: Chunked response.

#     Raises:
#     - Exception: If there is an error generating the response.
#     """
#     try:
#         messages = [
#             {"role": "system", "content": "You are an AI Document Q&A Chatbot, you must answer the question given by the user with respect to the context given. If a user greets you, you must greet them back politely"},
#             {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
#         ]

#         async with client.chat.completions.create(
#             model=deployment,
#             messages=messages,
#             temperature=0.5,
#             stream=True  # Enable streaming
#         ) as response_stream:
#             async for chunk in response_stream:
#                 yield chunk.choices[0].delta.content  # Adjust based on actual response format

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error generating response: {e}")



def chunk_text(text, chunk_size=1):
    """Chunk text into smaller parts of specified size."""
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])


def employee_ID(db_engine, token):
    """
    Retrieves the employee ID using an LDAP service.

    Args:
    - db_engine: SQLAlchemy database engine.
    - token (str): Token to decode and retrieve employee information.

    Returns:
    - str: Employee ID.

    Raises:
    - HTTPException: If there is an error retrieving the employee ID.
    """
    try:
        SessionLocal = sessionmaker(bind=db_engine)
        session = SessionLocal()
        url = f'https://ldapfastapi.salmonsmoke-83f22e73.uaenorth.azurecontainerapps.io/ldap/decode-token/?token={token}'
        response = requests.post(url, verify=False)
        user_info = response.json()
        employeeid = user_info['employeeid']
        return employeeid
    # except KeyError as e:
    #     raise HTTPException(status_code=400, detail=f"{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get employee ID: {str(e)}")



def create_agent(db_engine, llm):
    """
    Creates an SQL agent for interacting with a SQL database.
    
    Args:
    - db_engine: SQLAlchemy database engine.
    - llm: Language model for interacting with the SQL database.

    Returns:
    - object: SQL database agent.

    Raises:
    - RuntimeError: If there is an error creating the SQL agent.
    """
    try:
       
        db = SQLDatabase(db_engine, view_support=True, include_tables=["ProjectOrgView", "ProjectTasksStreamsView", "ProjectRequestsView", "ProjectApprovalsView"])
        sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)

        SQL_SUFFIX = get_suffix()

        
        sqldb_agent = create_sql_agent(
            llm=llm,
            toolkit=sql_toolkit,
            suffix=SQL_SUFFIX,
            input_variables=["input", "agent_scratchpad", "history"],
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            agent_executor_kwargs={"handle_parsing_errors": True}
        )

        return sqldb_agent
    except Exception as e:
        raise HTTPException(f"Failed to create agent: {str(e)}")



def get_response(sqldb_agent, user_query, emp_id):
    """
    Retrieves a response from an SQL agent based on user input.

    Args:
    - sqldb_agent: SQL database agent.
    - user_query (str): User query input.
    - emp_id (str): Employee ID.

    Returns:
    - str: Response generated by the SQL agent.

    Raises:
    - RuntimeError: If there is an error retrieving the response.
    """
    try:
        schema = get_schema()
        prompt = get_prompt(schema, user_query, emp_id)

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt),
                ("user", "{query}\n ai: ")
            ]
        )

        response = sqldb_agent.run(final_prompt.format(query=user_query))
        return response
    except Exception as e:
        raise HTTPException(f"Failed to get a response: {str(e)}")


# async def get_response(sqldb_agent, user_query, emp_id):
#     """
#     Retrieves a response from an SQL agent based on user input in streaming mode.

#     Args:
#     - sqldb_agent: SQL database agent.
#     - user_query (str): User query input.
#     - emp_id (str): Employee ID.

#     Yields:
#     - str: Chunked response.

#     Raises:
#     - RuntimeError: If there is an error retrieving the response.
#     """
#     try:
#         schema = get_schema()
#         prompt = get_prompt(schema, user_query, emp_id)

#         final_prompt = ChatPromptTemplate.from_messages(
#             [
#                 ("system", prompt),
#                 ("user", "{query}\n ai: ")
#             ]
#         )

#         async for chunk in sqldb_agent.run(final_prompt.format(query=user_query), stream=True):
#             yield chunk  # Adjust based on actual response format

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get a response: {e}")



def generate_session_name(query: str) -> str:
    """
    Generates a session name based on a query using an Azure OpenAI model.

    Args:
    - query (str): Query for generating the session name.

    Returns:
    - str: Generated session name.

    Raises:
    - Exception: If there is an error generating the session name.
    """
    try:
        session_name_creation = [
                {"role": "system", "content": "You are a good title creator for a chatbot session. Create a small, short and crisp one line (with three words maximum) title in the language of the {query}."},
                {"role": "user", "content": query}
            ]
        response = client.chat.completions.create(
            model=deployment,
            messages=session_name_creation,
            temperature=0,
            max_tokens=10
        )
        return response.choices[0].message.content.strip('"')
    except Exception as e:
        raise HTTPException(f"Error generating session name: {e}")
    


