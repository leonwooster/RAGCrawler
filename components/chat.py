from typing import List, Dict
import streamlit as st

class ChatComponent:
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
    
    def render_messages(self, messages: List[Dict]):
        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "sources" in message:
                    with st.expander("Sources"):
                        for source in message["sources"]:
                            st.write(f"- {source}")
    
    def process_query(self, query: str, chat_history: List[Dict]) -> Dict:
        context = self._build_context(chat_history)
        return self.rag_service.query(context + query) 