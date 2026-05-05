import os

# Force offline mode for the embedding model
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import chromadb
from chromadb.utils import embedding_functions
from langchain_core.tools import tool

# Setup absolute paths to ensure it always finds the database
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
db_path = os.path.join(root_dir, "chroma_db")

print("Initializing Catalog Search Tool...")

# Connect to ChromaDB
client = chromadb.PersistentClient(path=db_path)
hf_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client.get_collection(name="electronics_catalog", embedding_function=hf_ef)

@tool
def search_catalog(query: str) -> str:
    """
    Searches the electronics product catalog. 
    Use this tool WHENEVER the user asks for product recommendations, 
    is looking to buy something, or asks about electronics.
    
    Args:
        query: The search terms to look for (e.g., "cheap wireless mouse")
    """
    print(f"\n[Tool Execution] Agent is searching database for: '{query}'")
    
    # Perform the search
    results = collection.query(
        query_texts=[query],
        n_results=3 
    )
    
    # Format the results for the LLM
    if not results['documents'][0]:
        return "No products found for this query."
        
    formatted_results = []
    for i in range(len(results['documents'][0])):
        title = results['metadatas'][0][i]['title']
        price = results['metadatas'][0][i]['price']
        categories = results['metadatas'][0][i]['categories']
        
        # Clean up missing prices
        display_price = "Price unavailable" if str(price).lower() == "nan" else f"${price}"
            
        formatted_results.append(
            f"Product {i+1}:\n"
            f"- Title: {title}\n"
            f"- Price: {display_price}\n"
            f"- Category: {categories}\n"
        )
        
    return "\n".join(formatted_results)