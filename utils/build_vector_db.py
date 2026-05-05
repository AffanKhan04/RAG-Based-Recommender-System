import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm
import os

def build_vector_database(parquet_path: str, db_path: str, collection_name: str, batch_size: int = 500):
    print(f"Loading cleaned data from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    df['asin'] = df['asin'].astype(str).str.strip()
    df = df[df['asin'] != ""]
    df = df.drop_duplicates(subset=['asin'])
    
    total_records = len(df)
    print(f"Found {total_records} UNIQUE records after deduplication.")

    print(f"Initializing ChromaDB at {db_path}...")
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    hf_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    # Pass the embedding function to the collection
    collection = chroma_client.get_or_create_collection(
        name=collection_name, 
        embedding_function=hf_ef
    )

    print(f"Starting embedding generation via 'all-MiniLM-L6-v2'")
    
    # Process in batches to avoid memory crashes
    for i in tqdm(range(0, total_records, batch_size), desc="Batches Processed"):
        batch_df = df.iloc[i : i + batch_size]
        
        ids = batch_df['asin'].tolist()
        documents = batch_df['combined_text'].tolist()
        
        metadatas = batch_df.apply(
            lambda row: {
                "title": row['title'],
                "price": row['price'],
                "categories": row['categories']
            }, axis=1
        ).tolist()

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    print("\nVector database is fully populated and ready for RAG.")

if __name__ == "__main__":
    os.makedirs("chroma_db", exist_ok=True)
    
    PARQUET_FILE = "data/cleaned_electronics.parquet"
    DB_FOLDER = "chroma_db"
    COLLECTION_NAME = "electronics_catalog"
    
    build_vector_database(PARQUET_FILE, DB_FOLDER, COLLECTION_NAME)