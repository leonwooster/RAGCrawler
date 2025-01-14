from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from src.services.vector_store_service import VectorStoreService
from typing import Dict, List, Any

class RAGService:
    def __init__(self, vector_store_service: VectorStoreService):
        self.vector_store_service = vector_store_service
        self.llm = ChatOpenAI(temperature=0)
        self.chain = None

    def _create_chain(self, prompt_template: str):
        """Create a chain with the given prompt template."""
        # Create prompt from template
        prompt = PromptTemplate.from_template(prompt_template)
        
        # Create chain using the new constructor
        chain = create_stuff_documents_chain(
            llm=self.llm,
            prompt=prompt,
            document_variable_name="context"
        )
        
        return chain

    def initialize_chain(self):
        """Initialize the chain with conversation context handling."""
        prompt_template = """
        Context from previous conversation:
        {context}
        
        Based on the following documents and the conversation context above, 
        please answer the question. If you cannot answer the question based 
        on the documents provided, please say so.

        Documents: {context}
        
        Question: {question}
        
        Answer:"""

        self.chain = self._create_chain(prompt_template)

    def query(self, query: str) -> Dict[str, Any]:
        """
        Query the RAG system with context awareness.
        
        Args:
            query: The user's question
            
        Returns:
            Dict containing the answer and source documents
        """
        if not self.chain:
            raise ValueError("Chain not initialized")
            
        # Extract relevant documents
        docs = self.vector_store_service.vector_store.similarity_search(query)
        
        try:
            # Use invoke instead of run
            response = self.chain.invoke({
                "context": docs,
                "question": query
            })
            
            return {
                "answer": response,
                "source_documents": docs
            }
        except Exception as e:
            raise Exception(f"Error during query processing: {str(e)}")

    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        Get relevant documents for a query.
        
        Args:
            query: The search query
            
        Returns:
            List of relevant documents
        """
        return self.vector_store_service.vector_store.similarity_search(query) 