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
        return RAGService(vector_store_service)
    return None

def main():
    # Initialize session state for RAG service
    if 'rag_service' not in st.session_state:
        st.session_state.rag_service = initialize_rag_service()

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
        st.header("Search Crawled Content")
        query = st.text_input("Enter your question")
        
        if st.button("Search"):
            if st.session_state.rag_service is None:
                st.warning("Please crawl a website first!")
            else:
                try:
                    response = st.session_state.rag_service.query(query)
                    
                    st.subheader("Answer:")
                    st.write(response["answer"])
                    
                    st.subheader("Sources:")
                    for doc in response["source_documents"]:
                        st.write(f"- {doc.metadata['url']}")
                    
                except Exception as e:
                    st.error(f"Error during search: {str(e)}")
    
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