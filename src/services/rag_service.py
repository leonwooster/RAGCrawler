from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from src.services.vector_store_service import VectorStoreService

class RAGService:
    def __init__(self, vector_store_service: VectorStoreService):
        self.vector_store_service = vector_store_service
        self.llm = ChatOpenAI(temperature=0)
        self.chain = None
        
    def initialize_chain(self):
        if not self.vector_store_service.vector_store:
            raise ValueError("Vector store not initialized")
            
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store_service.vector_store.as_retriever(),
            return_source_documents=True
        )
        
    def query(self, question: str, chat_history: list = []):
        if not self.chain:
            raise ValueError("Chain not initialized")
            
        response = self.chain({"question": question, "chat_history": chat_history})
        return response 