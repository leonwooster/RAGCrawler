from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import os

class VectorStoreService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.persist_directory = "chroma_db"
        # Try to load existing vector store
        if os.path.exists(self.persist_directory):
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        else:
            self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def create_vector_store(self, documents: List[Dict]):
        texts = []
        metadatas = []
        
        for doc in documents:
            chunks = self.text_splitter.split_text(doc['content'])
            texts.extend(chunks)
            metadatas.extend([{'url': doc['url'], 'title': doc['title']} for _ in chunks])
        
        self.vector_store = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=self.persist_directory
        )
        
    def similarity_search(self, query: str, k: int = 4):
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        return self.vector_store.similarity_search(query, k=k) 