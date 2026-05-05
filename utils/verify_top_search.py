import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
# os.environ["HF_TOKEN"] = "your_token_here" # Uncomment if you add a token

import chromadb
from chromadb.utils import embedding_functions

def interactive_search():
    print("🔌 Connecting to local ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")
    
    hf_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    try:
        collection = client.get_collection(
            name="electronics_catalog",
            embedding_function=hf_ef
        )
        print(f"✅ Database connected! ({collection.count()} records)")
        
        # The Interactive Loop Starts Here
        print("\n" + "="*50)
        print("🛒 WELCOME TO THE ELECTRONICS SEARCH ENGINE")
        print("Type 'quit' or 'exit' to stop.")
        print("="*50)

        while True:
            # 1. Get user input dynamically
            query = input("\n🔎 What are you looking for? \n> ")
            
            # 2. Check if the user wants to quit
            if query.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
                
            # 3. Skip empty searches
            if not query.strip():
                continue
                
            print(f"Searching for: '{query}'...\n")
            
            # 4. Perform the search with the dynamic query
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
            
            # 5. Print the results
            print("--- Top 3 Matches ---")
            for i in range(len(results['documents'][0])):
                print(f"Rank {i+1}:")
                print(f"Title: {results['metadatas'][0][i]['title']}")
                print(f"Price: {results['metadatas'][0][i]['price']}")
                print("-" * 20)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    interactive_search()