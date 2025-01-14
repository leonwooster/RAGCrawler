from bs4 import BeautifulSoup
import requests
from typing import List, Dict
from urllib.parse import urljoin, urlparse
import asyncio
import aiohttp
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CrawlerService:
    def __init__(self):
        self.visited_urls = set()
        self.results = []
        
    async def crawl(self, base_url: str, max_pages: int = 10) -> List[Dict]:
        self.visited_urls.clear()
        self.results.clear()
        
        async with aiohttp.ClientSession() as session:
            await self._crawl_url(session, base_url, max_pages)
        
        return self.results
    
    async def _crawl_url(self, session: aiohttp.ClientSession, url: str, max_pages: int):
        if len(self.visited_urls) >= max_pages or url in self.visited_urls:
            return
            
        try:
            self.visited_urls.add(url)
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract text content
                    text_content = ' '.join([p.get_text() for p in soup.find_all('p')])
                    
                    self.results.append({
                        'url': url,
                        'title': soup.title.string if soup.title else '',
                        'content': text_content
                    })
                    
                    # Find and crawl links
                    links = soup.find_all('a')
                    tasks = []
                    for link in links:
                        href = link.get('href')
                        if href:
                            full_url = urljoin(url, href)
                            if urlparse(full_url).netloc == urlparse(url).netloc:
                                tasks.append(self._crawl_url(session, full_url, max_pages))
                    
                    await asyncio.gather(*tasks)
                    
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}") 