from azure.storage.blob import BlobServiceClient
from operator import itemgetter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools.render import render_text_description
from functions import load_faiss_data_from_npy, search_vector_store, generate_response, get_response, llm, create_agent 
from langchain_core.tools import tool
from config import config as config
from langchain_core.output_parsers import JsonOutputParser
from database.__init__ import get_conn, conn_mongodb
from pymongo import MongoClient

# Load configuration
storage_string = config["BLOB-STORAGE-STRING"]["STRING"]
blob_service_client = BlobServiceClient.from_connection_string(storage_string)
container_name = "day-chatbot-file" 
connection_string = config["BLOB-STORAGE-STRING"]["STRING"]  

# faiss_data = load_faiss_data_from_npy(container_name, storage_string) # load data from azure blob storage
directory_path = "C:/Users/mmurtuza001/chatbot new pdf/"
faiss_data = load_faiss_data_from_npy(directory_path)

emp_id_storage = {} #emp_id storage
db= get_conn() # Connect to database
agent = create_agent(db, llm) # Create agent for language model
collection = conn_mongodb() # Connect to MongoDB collection


@tool
def handle_vector_query(query:str): 
    """this tool helps users guide themselves through the website by helping them find solutions for creating projects, tasks etc or for navigating through the website. Also it can be used for greeting."""
    try:
        top_k_texts = search_vector_store(faiss_data["index"], faiss_data["texts"], query, k=3)
        context = " ".join(top_k_texts)
        print(query)
        answer =  generate_response(query, context)
        return answer
    except Exception as e:
        raise RuntimeError(status_code=500, detail=f"Error processing request: {e}")


@tool
def handle_sql_query(query: str):
    """ this tool helps with specific user queries on tasks, projects, streams, approvals etc"""
    try:
        emp_id = emp_id_storage.get('emp_id')
        print(emp_id)
        # emp_id = emp_id_storage.get('emp_id')
        response = get_response(agent, query, emp_id)

        return  response
    except Exception as e:
        raise RuntimeError(status_code=500, detail=f"Error processing request: {e}")


tools = [handle_vector_query, handle_sql_query]


def tool_chain(model_output):
    """
    Function to choose and invoke the appropriate tool based on model output.

    Args:
    - model_output (dict): Output from the language model.

    Returns:
    - dict: Response generated by the chosen tool.
    """
    tool_map = {tool.name: tool for tool in tools}
    chosen_tool = tool_map[model_output["name"]]
    return itemgetter("arguments") | chosen_tool

def get_last_n_messages(emp_id, session_id, n=5):
    
    # Find the chat history for the emp_id and session_id and limit to last n messages
    chat_history = collection.find_one(
        {"emp_id": emp_id, "sessions.session_id": session_id},
        {"sessions.$": 1}
    )
    
    if chat_history and "sessions" in chat_history:
        messages = chat_history["sessions"][0]["messages"]
        return messages[-n:]  # Get the last n messages
    
    return []

def call_tools(query, emp_id, session_id):
    """
    Function to call tools asynchronously based on user input.

    Args:
    - query (str): User input query.
    - emp_id (str): Employee ID for context (stored globally).

    Returns:
    - dict: Final response generated by the tool chain.
    """
    try:
        
        emp_id_storage['emp_id'] = emp_id

        last_messages = get_last_n_messages(emp_id, session_id, n=5)
        chat_history = [(msg["type"], msg["content"]) for msg in last_messages]

        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )
        
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        contextualize_q_chain = contextualize_q_prompt | llm

        # Reformulate the query
        reformulated_query = contextualize_q_chain.invoke(
            {"input": query, "chat_history": chat_history}
        )
        # Render tools description
        rendered_tools = render_text_description(tools)
        system_prompt = f"""You are an assistant that has access to the following set of tools. Here are the names and descriptions for each tool:

        {rendered_tools}

        Given the user input, return the name and input of the tool to use. Return your response as a JSON blob with 'name' and 'arguments' keys."""
        
        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("user", "{input}")]
        )
        
        chain = prompt | llm | JsonOutputParser() | tool_chain
        final_response = chain.invoke(reformulated_query)
        
        return final_response
    
    except Exception as e:
        raise RuntimeError(f"Error processing request: {str(e)}")