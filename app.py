import streamlit as st
import asyncio
from src.services.crawler_service import CrawlerService
from src.services.vector_store_service import VectorStoreService
from src.services.rag_service import RAGService
from src.models.database import init_db, CrawlHistory
import os

# Initialize services
crawler_service = CrawlerService()
vector_store_service = VectorStoreService()

# Initialize database
db_session = init_db()

def initialize_rag_service():
    """Initialize RAG service if vector store exists and return it"""
    if vector_store_service.vector_store is not None:
        rag_service = RAGService(vector_store_service)
        rag_service.initialize_chain()  # Initialize the chain immediately
        return rag_service
    return None

def main():
    # Initialize session state variables
    if 'rag_service' not in st.session_state:
        st.session_state.rag_service = initialize_rag_service()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    st.title("Web Crawler and RAG Search System")
    
    # Sidebar for OpenAI API Key
    with st.sidebar:
        api_key = st.text_input("OpenAI API Key", type="password")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            # Reinitialize services if API key is provided
            if st.session_state.rag_service is None and vector_store_service.vector_store is not None:
                st.session_state.rag_service = RAGService(vector_store_service)
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Crawler", "RAG Search", "History"])
    
    # Crawler Section
    with tab1:
        st.header("Web Crawler")
        url = st.text_input("Enter URL to crawl")
        max_pages = st.number_input("Maximum pages to crawl", min_value=1, value=10)
        
        if st.button("Start Crawling"):
            with st.spinner("Crawling website..."):
                try:
                    # Run crawler
                    crawl_results = asyncio.run(crawler_service.crawl(url, max_pages))
                    
                    # Store results in vector store
                    vector_store_service.create_vector_store(crawl_results)
                    
                    # Initialize RAG service
                    st.session_state.rag_service = RAGService(vector_store_service)
                    st.session_state.rag_service.initialize_chain()
                    
                    # Save to database
                    crawl_history = CrawlHistory(
                        url=url,
                        status=True,
                        pages_crawled=len(crawl_results)
                    )
                    db_session.add(crawl_history)
                    db_session.commit()
                    
                    st.success(f"Successfully crawled {len(crawl_results)} pages!")
                    
                except Exception as e:
                    st.error(f"Error during crawling: {str(e)}")
                    crawl_history = CrawlHistory(
                        url=url,
                        status=False,
                        error_message=str(e)
                    )
                    db_session.add(crawl_history)
                    db_session.commit()
    
    # RAG Search Section
    with tab2:
        st.header("Chat with Your Documents")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "sources" in message:
                    with st.expander("Sources"):
                        for source in message["sources"]:
                            st.write(f"- {source}")

        # Chat input
        if query := st.chat_input("Ask a question about the crawled content"):
            if not os.getenv("OPENAI_API_KEY"):
                st.warning("Please enter your OpenAI API key in the sidebar first!")
                return
            
            if st.session_state.rag_service is None:
                st.warning("Please crawl a website first!")
                return

            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.write(query)

            # Generate response
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking..."):
                        # Get response with context from chat history
                        context = "\n".join([
                            f"{msg['role']}: {msg['content']}" 
                            for msg in st.session_state.chat_history[-3:]  # Use last 3 messages for context
                        ])
                        
                        # Combine context with current query
                        contextualized_query = f"""
                        Previous conversation:
                        {context}
                        
                        Current question: {query}
                        
                        Please provide a response that takes into account the conversation history.
                        """
                        
                        response = st.session_state.rag_service.query(contextualized_query)
                        
                        # Display the response
                        st.write(response["answer"])
                        
                        # Store sources
                        sources = [doc.metadata['url'] for doc in response["source_documents"]]
                        with st.expander("Sources"):
                            for source in sources:
                                st.write(f"- {source}")
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response["answer"],
                            "sources": sources
                        })
                        
                        # Update chat history for context
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": query
                        })
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response["answer"]
                        })

                except Exception as e:
                    st.error(f"Error during search: {str(e)}")

        # Add a button to clear chat history
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()
    
    # History Section
    with tab3:
        st.header("Crawl History")
        history = db_session.query(CrawlHistory).order_by(CrawlHistory.timestamp.desc()).all()
        
        for entry in history:
            status = "✅" if entry.status else "❌"
            st.write(f"{status} {entry.url} - {entry.timestamp}")
            if entry.error_message:
                st.write(f"Error: {entry.error_message}")
            st.write("---")

if __name__ == "__main__":
    main() 