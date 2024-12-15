# SQL-Chatbot

## **Overview**  

This Chatbot functions as a Dual Query Chatbot which is designed to interact seamlessly with both structured SQL databases and unstructured data represented by vector embeddings. Using LangChain's advanced tool-calling capabilities, the chatbot dynamically decides whether to query an SQL database or leverage vector embeddings based on user input.  

## **Features**  
- **Dual Query Handling**:  
  - Handles SQL-based queries for structured data.  
  - Supports vector-based queries for semantic search or similarity matching.  
- **Tool Calling**: Powered by LangChain's tool-calling framework for dynamic query resolution.  
- **Vector Search**: Utilizes FAISS (Facebook AI Similarity Search) for efficient vector embedding management.  
- **SQL Agent**: Employs LangChain's SQL agents for precise database queries.  

## **Technologies Used**  
- **LangChain**: For tool calling and SQL agents.  
- **FAISS**: For managing and querying vector embeddings.  
- **Python**: Backend development.  

## **Setup Instructions**  

### **1. Prerequisites**  
- Python 3.8 or higher installed.  
- A configured SQL database.  
- A vector database or embedding storage.  

### **2. Installation**  
Clone the repository:  
git clone <URL>
cd file_name

Install the dependencies.

### **3. Configure Database and Embeddings**
Update the config.py file with your SQL database credentials.
Add your FAISS vector index file or set up FAISS from scratch.

### **4. Run the Chatbot**
uvicorn main:app --reload

## **Usage**
1. Ask SQL-related queries, such as:
"How many users registered last month?"
2. Ask semantic questions for vector embeddings, such as:
"Explain the document in few sentences"
The chatbot will automatically route the query to the appropriate tool.

## **How It Works**
1. The user inputs a query.
2. The chatbot analyzes the intent using LangChain's tool-calling mechanism.
3. Based on the intent:
- SQL Agent queries the SQL database.
- Vector Search uses FAISS for similarity-based results.

