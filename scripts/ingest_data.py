import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv  # <-- IMPORT THE LIBRARY
# Define the path to the folder containing your documents
load_dotenv() # This will find and load the variables from your .env file

# Define the path to the folder containing your documents

DATA_PATH = "data/knowledge_base"
# Define the path where the FAISS index will be stored
DB_FAISS_PATH = "faiss_index"

def main():
    """
    Main function to create a vector database from documents.
    """
    print("--- Starting data ingestion process ---")

    # 1. No API key needed for local embeddings
    print("Using local embeddings - no API key required")
    
    # 2. Clean up old database files
    if os.path.exists(DB_FAISS_PATH):
        print(f"Removing existing database at {DB_FAISS_PATH}")
        shutil.rmtree(DB_FAISS_PATH)

    # 3. Load the documents from the specified directory using PyPDFLoader (stable on Windows)
    loader = DirectoryLoader(
        DATA_PATH,
        glob='**/*.pdf',
        loader_cls=PyPDFLoader,
        use_multithreading=True,
        show_progress=True
    )
    documents = loader.load()
    if not documents:
        print("No documents found. Please add PDF or TXT files to the data/knowledge_base folder.")
        return
    print(f"Loaded {len(documents)} documents.")

    # 4. Split the documents into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"Split documents into {len(chunks)} chunks.")

    # 5. Create embeddings for the chunks using local model
    # Using a lightweight but effective embedding model
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': 'cpu'},  # Use CPU for compatibility
        encode_kwargs={'normalize_embeddings': True}
    )

    # 6. Create a FAISS vector store from the chunks and embeddings
    print("Creating FAISS vector store... This may take a few minutes.")
    vector_store = FAISS.from_documents(chunks, embeddings)

    # 7. Save the vector store locally
    vector_store.save_local(DB_FAISS_PATH)
    print("--- 🚀 Data ingestion complete! ---")
    print(f"Vector store saved locally at: {DB_FAISS_PATH}")

if __name__ == "__main__":
    main()