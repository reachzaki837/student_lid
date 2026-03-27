import os
import io
import networkx as nx
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangchainDocument
from app.models.user import Material

# We will store the local FAISS index in the app directory for simplicity
INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "faiss_index")
os.makedirs(INDEX_DIR, exist_ok=True)

# Local Free Embeddings (runs on CPU fast)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

class RAGService:
    @staticmethod
    async def process_upload(file_bytes: bytes, filename: str, uploader_email: str) -> bool:
        """Processes an uploaded file, extracts text, chunks it, and adds to FAISS index."""
        try:
            # 1. Extract Text
            content = ""
            if filename.lower().endswith(".pdf"):
                pdf = PdfReader(io.BytesIO(file_bytes))
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n"
            else:
                content = file_bytes.decode('utf-8')
            
            # Save the material to MongoDB
            material = Material(uploader_email=uploader_email, filename=filename, content_text=content)
            await material.insert()

            # 2. Chunk the text
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_text(content)
            
            docs = [
                LangchainDocument(
                    page_content=chunk,
                    metadata={"source": filename, "uploader": uploader_email}
                ) for chunk in chunks
            ]
            
            # 3. Add to FAISS Vector Store
            try:
                vectorstore = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
                vectorstore.add_documents(docs)
                vectorstore.save_local(INDEX_DIR)
            except Exception:
                # Create a new index if it doesn't exist
                vectorstore = FAISS.from_documents(docs, embeddings)
                vectorstore.save_local(INDEX_DIR)
                
            return True
        except Exception as e:
            print(f"Error processing document: {e}")
            return False

    @staticmethod
    def query_documents(query: str, top_k: int = 3) -> str:
        """Queries the FAISS index to act as the retriever for GraphRAG/Standard RAG."""
        try:
            if not os.path.exists(os.path.join(INDEX_DIR, "index.faiss")):
                return "No specific course materials found."
            
            vectorstore = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
            results = vectorstore.similarity_search(query, k=top_k)
            context = "\n\n".join([f"Source: {res.metadata.get('source', 'Unknown')}\nContent: {res.page_content}" for res in results])
            return context
        except Exception as e:
            print(f"FAISS Query Error: {e}")
            return "No specific course materials found."
