from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import os
import logging

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        # Try to load existing vector store during initialization
        self.vector_store = self.load_vector_store()
        
    def create_vector_store(self, documents: List[Dict[str, str]]):
        """Create a new vector store from the provided documents"""
        try:
            # Process the documents
            texts = []
            metadatas = []
            
            for doc in documents:
                chunks = self.text_splitter.split_text(doc['content'])
                texts.extend(chunks)
                # Create metadata for each chunk
                chunk_metadata = [{'url': doc['url'], 'title': doc.get('title', '')} for _ in chunks]
                metadatas.extend(chunk_metadata)
            
            # Create the vector store
            self.vector_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            
            # Save the vector store
            self.save_vector_store()
            logger.info("Vector store created and saved successfully")
            
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise
    
    def save_vector_store(self):
        """Save the vector store to disk"""
        if self.vector_store:
            try:
                os.makedirs('vector_store', exist_ok=True)
                self.vector_store.save_local(
                    'vector_store',
                    allow_dangerous_deserialization=True  # We trust our own saved data
                )
                logger.info("Vector store saved successfully")
            except Exception as e:
                logger.error(f"Error saving vector store: {str(e)}")
                raise
    
    def load_vector_store(self):
        """Load the vector store from disk"""
        try:
            if os.path.exists('vector_store'):
                vector_store = FAISS.load_local(
                    'vector_store',
                    self.embeddings,
                    allow_dangerous_deserialization=True  # We trust our own saved data
                )
                logger.info("Vector store loaded successfully")
                return vector_store
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
        return None

    def similarity_search(self, query: str, k: int = 4):
        """Perform similarity search"""
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        return self.vector_store.similarity_search(query, k=k) 