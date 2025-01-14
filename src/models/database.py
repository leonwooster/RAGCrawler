from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class CrawlHistory(Base):
    __tablename__ = 'crawl_history'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(Boolean, default=False)
    pages_crawled = Column(Integer, default=0)
    error_message = Column(String, nullable=True)

def init_db():
    engine = create_engine('sqlite:///crawler_rag.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session() 