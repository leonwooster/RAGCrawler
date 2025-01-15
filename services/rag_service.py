from functools import lru_cache
from ratelimit import limits, sleep_and_retry

class RAGService:
    @sleep_and_retry
    @limits(calls=50, period=60)  # 50 calls per minute
    @lru_cache(maxsize=100)
    def query(self, query: str) -> Dict:
        # Existing query logic
        pass 