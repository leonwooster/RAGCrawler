import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
import logging
from urllib.parse import urljoin, urlparse
import os
import chardet
from aiohttp import TCPConnector
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
from datetime import datetime
import sys

# Increase recursion limit
sys.setrecursionlimit(10000)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('logs/crawler.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

class CrawlerService:
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.session = None
        self.rate_limit = 1  # Seconds between requests
        self.last_request_time = 0
        self.batch_size = 5  # Reduced batch size
        self.progress = None
        self.task_id = None
        self.max_content_length = 100000  # Maximum content length in characters
        
    def truncate_content(self, content: str) -> str:
        """Truncate content to maximum length"""
        if len(content) > self.max_content_length:
            return content[:self.max_content_length]
        return content

    async def is_valid_url(self, url: str, base_url: str) -> bool:
        """Check if URL is valid and belongs to the same domain"""
        try:
            if not url:
                return False
            # Parse URLs
            parsed_url = urlparse(url)
            parsed_base = urlparse(base_url)
            
            # Skip certain file types and patterns
            skip_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js'}
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                return False
                
            # Skip URLs with fragments or queries
            if parsed_url.fragment or parsed_url.query:
                return False
                
            # Check if URLs belong to the same domain
            return parsed_url.netloc == parsed_base.netloc or not parsed_url.netloc
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False

    async def respect_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time = time.time()

    async def extract_text(self, response: aiohttp.ClientResponse, url: str) -> Optional[Dict[str, str]]:
        """Extract text content from response"""
        try:
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'text/html' not in content_type:
                logger.info(f"Skipping non-HTML content type ({content_type}): {url}")
                return None
                
            content = await response.read()
            if len(content) > 1024 * 1024:  # Skip files larger than 1MB
                logger.info(f"Skipping large file: {url}")
                return None
                
            encoding = chardet.detect(content)['encoding'] or 'utf-8'
            text = content.decode(encoding, errors='replace')
            
            # Try lxml first, fall back to html.parser if lxml is not available
            try:
                soup = BeautifulSoup(text, 'lxml')
            except:
                soup = BeautifulSoup(text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                element.decompose()
            
            # Get text and title
            text = ' '.join(soup.get_text(separator=' ', strip=True).split())
            text = self.truncate_content(text)  # Truncate long content
            title = soup.title.string if soup.title else url
            
            # Extract links (limited number)
            links = []
            for link in soup.find_all('a', href=True, limit=100):  # Limit number of links
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    links.append(full_url)
            
            # Clear soup to free memory
            soup.decompose()
            
            return {
                'url': url,
                'title': title[:500],  # Limit title length
                'content': text,
                'links': links[:100]  # Limit number of links
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None
        finally:
            # Force garbage collection
            if 'soup' in locals():
                del soup
            if 'content' in locals():
                del content
            if 'text' in locals():
                del text

    async def crawl_url(self, url: str, base_url: str) -> Optional[Dict]:
        """Crawl a single URL"""
        if url in self.visited_urls:
            return None
            
        self.visited_urls.add(url)
        await self.respect_rate_limit()
        
        try:
            if not await self.is_valid_url(url, base_url):
                return None
                
            async with self.session.get(url, timeout=30, ssl=False) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    return None
                    
                result = await self.extract_text(response, url)
                if result and self.progress and self.task_id:
                    self.progress.update(self.task_id, advance=1)
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout while crawling {url}")
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
        return None

    async def process_batch(self, urls: List[str], base_url: str) -> List[Dict]:
        """Process a batch of URLs concurrently"""
        tasks = []
        for url in urls:
            if len(tasks) >= self.batch_size:
                # Wait for some tasks to complete before adding more
                completed, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in completed:
                    result = await task
                    if result:
                        yield result
                        
            tasks.append(asyncio.create_task(self.crawl_url(url, base_url)))
        
        # Wait for remaining tasks
        if tasks:
            completed, _ = await asyncio.wait(tasks)
            for task in completed:
                result = await task
                if result:
                    yield result

    async def crawl(self, start_url: str, max_pages: int = 10) -> List[Dict]:
        """Crawl website starting from given URL"""
        # Limit maximum pages to prevent memory issues
        max_pages = min(max_pages, 10000)
        
        self.visited_urls.clear()
        results = []
        urls_to_crawl = [start_url]
        start_time = datetime.now()
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Create aiohttp session with connection pooling and limits
        connector = TCPConnector(
            limit=self.batch_size,
            force_close=True,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            raise_for_status=False
        ) as session:
            self.session = session
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                self.progress = progress
                self.task_id = progress.add_task(f"Crawling {start_url}...", total=max_pages)
                
                try:
                    while urls_to_crawl and len(results) < max_pages:
                        # Process URLs in batches
                        batch = urls_to_crawl[:self.batch_size]
                        urls_to_crawl = urls_to_crawl[self.batch_size:]
                        
                        async for result in self.process_batch(batch, start_url):
                            if result and len(result['content'].strip()) > 0:
                                results.append({
                                    'url': result['url'],
                                    'title': result['title'],
                                    'content': result['content']
                                })
                                
                                # Add new URLs to crawl
                                new_urls = [
                                    url for url in result.get('links', [])
                                    if url not in self.visited_urls
                                ][:100]  # Limit number of new URLs per page
                                urls_to_crawl.extend(new_urls)
                                
                                if len(results) >= max_pages:
                                    break
                                
                        # Log progress
                        logger.info(f"Crawled {len(results)} pages. Queue size: {len(urls_to_crawl)}")
                        
                        # Clear completed URLs from memory
                        urls_to_crawl = urls_to_crawl[-1000:]  # Keep only last 1000 URLs
                        
                except Exception as e:
                    logger.error(f"Error during crawl: {str(e)}")
                finally:
                    end_time = datetime.now()
                    duration = end_time - start_time
                    logger.info(f"Crawling completed. Total pages: {len(results)}. Duration: {duration}")
                    
        return results 