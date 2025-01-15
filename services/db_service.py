from sqlalchemy.orm import Session
from contextlib import contextmanager

class DatabaseService:
    def __init__(self, session: Session):
        self.session = session
    
    @contextmanager
    def transaction(self):
        try:
            yield self.session
            self.session.commit()
        except:
            self.session.rollback()
            raise
        finally:
            self.session.close()
    
    async def save_crawl_history(self, url: str, status: bool, pages_crawled: int = 0, error_message: str = None):
        with self.transaction() as session:
            crawl_history = CrawlHistory(
                url=url,
                status=status,
                pages_crawled=pages_crawled,
                error_message=error_message
            )
            session.add(crawl_history) 