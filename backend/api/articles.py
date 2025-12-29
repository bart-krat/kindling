import os
import re
import time
import base64
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from serp import SERPProfileSearcher

# Load environment variables
load_dotenv(dotenv_path='.env')


class ArticleSearcher:
    def __init__(self, debug: bool = False):
        """
        Initialize article searcher using SERP API
        
        Args:
            debug: Print debug information
        """
        self.debug = debug
        self.serp_searcher = SERPProfileSearcher(debug=debug)
        
        # Get DataForSEO credentials for direct API calls
        self.login = os.getenv('DATAFORSEO_LOGIN')
        self.password = os.getenv('DATAFORSEO_PASSWORD')
        
        if not self.login or not self.password:
            raise ValueError(
                "DataForSEO credentials required. Set DATAFORSEO_LOGIN and "
                "DATAFORSEO_PASSWORD in .env file"
            )
        
        # Google News API endpoint
        self.news_api_url = "https://api.dataforseo.com/v3/serp/google/news/live/advanced"
        
        # Create basic auth header
        credentials = f"{self.login}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.api_headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        # Headers for downloading articles
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def search_google_news(self, query: str, location_code: int = 2826, language_code: str = "en") -> Optional[Dict]:
        """
        Search Google News using DataForSEO SERP API
        
        Args:
            query: Search query
            location_code: Location code (2826 = United States)
            language_code: Language code (en = English)
            
        Returns:
            API response dictionary or None
        """
        try:
            if self.debug:
                print(f"  Searching Google News: {query}")
            
            payload = [
                {
                    "keyword": query,
                    "location_code": location_code,
                    "language_code": language_code,
                    "device": "desktop",
                    "os": "windows"
                }
            ]
            
            response = requests.post(
                self.news_api_url,
                headers=self.api_headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if self.debug:
                    if 'tasks' in data and len(data['tasks']) > 0:
                        task = data['tasks'][0]
                        if 'status_code' in task:
                            print(f"  ✓ API Response: Status {task['status_code']}")
                        if 'result' in task and len(task['result']) > 0:
                            result = task['result'][0]
                            if 'items_count' in result:
                                print(f"  ✓ Found {result['items_count']} news results")
                
                return data
            else:
                if self.debug:
                    print(f"  ✗ API Error: HTTP {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"    Error: {error_data}")
                    except:
                        print(f"    Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def search_articles(self, name: str, top_n: int = 5) -> List[str]:
        """
        Search for articles about a person using Google News SERP API
        
        Args:
            name: Person's name to search for
            top_n: Number of top articles to return (default: 5)
            
        Returns:
            List of article URLs
        """
        try:
            if self.debug:
                print(f"Searching for articles about: {name}")
            
            # Search query: person's name
            query = f'"{name}"'
            
            # Use Google News API to search
            api_response = self.search_google_news(query)
            
            if not api_response:
                if self.debug:
                    print("  ✗ No results from SERP API")
                return []
            
            # Debug: Check API response structure
            if self.debug:
                try:
                    if 'tasks' in api_response and len(api_response['tasks']) > 0:
                        task = api_response['tasks'][0]
                        if 'result' in task and len(task['result']) > 0:
                            result = task['result'][0]
                            if 'items' in result:
                                print(f"  API returned {len(result['items'])} news items")
                                # Show first few items for debugging
                                for i, item in enumerate(result['items'][:5], 1):
                                    if 'url' in item:
                                        print(f"    Item {i}: {item.get('url', 'N/A')}")
                                    elif 'link' in item:
                                        print(f"    Item {i}: {item.get('link', 'N/A')}")
                except Exception as e:
                    print(f"  Debug error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Extract URLs from Google News results
            all_urls = []
            try:
                if 'tasks' not in api_response:
                    return []
                
                for task in api_response['tasks']:
                    if 'result' not in task:
                        continue
                    
                    for result_item in task['result']:
                        if 'items' not in result_item:
                            continue
                        
                        for item in result_item['items']:
                            # Google News might use 'url' or 'link' field
                            url = item.get('url') or item.get('link')
                            if url:
                                all_urls.append(url)
            except Exception as e:
                if self.debug:
                    print(f"  ⚠ Error extracting URLs: {e}")
                return []
            
            if self.debug:
                print(f"  Total URLs from SERP: {len(all_urls)}")
            
            # Filter out non-article URLs (social media, profiles, etc.)
            article_urls = []
            excluded_patterns = [
                'linkedin.com',
                'twitter.com',
                'x.com',
                'instagram.com',
                'facebook.com',
                'youtube.com',
                'tiktok.com',
                '/profile',
                '/user/',
                '/author/',
            ]
            
            filtered_count = 0
            for url in all_urls:
                # Skip excluded patterns
                excluded = False
                excluded_reason = None
                for pattern in excluded_patterns:
                    if pattern in url.lower():
                        excluded = True
                        excluded_reason = pattern
                        break
                
                if excluded:
                    filtered_count += 1
                    if self.debug:
                        print(f"    Filtered out ({excluded_reason}): {url}")
                    continue
                
                # Prefer news sites, blogs, and article-like URLs
                article_urls.append(url)
                
                if len(article_urls) >= top_n:
                    break
            
            if self.debug:
                print(f"  ✓ Found {len(article_urls)} article URLs (after filtering out {filtered_count})")
                for i, url in enumerate(article_urls, 1):
                    print(f"    {i}. {url}")
            
            return article_urls[:top_n]
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching articles: {e}")
                import traceback
                traceback.print_exc()
            return []
    
    def download_article_html(self, url: str) -> Optional[str]:
        """
        Download HTML content from an article URL
        
        Args:
            url: Article URL
            
        Returns:
            HTML content as string or None
        """
        try:
            if self.debug:
                print(f"  Downloading: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Check if it's HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                if self.debug:
                    print(f"    ⚠ Not HTML content: {content_type}")
                return None
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"    ✗ Error downloading: {e}")
            return None
        except Exception as e:
            if self.debug:
                print(f"    ✗ Unexpected error: {e}")
            return None
    
    def detect_paywall(self, html: str, soup: BeautifulSoup) -> bool:
        """
        Detect if article is behind a paywall
        
        Args:
            html: HTML content
            soup: BeautifulSoup object
            
        Returns:
            True if paywall detected, False otherwise
        """
        # Common paywall indicators
        paywall_indicators = [
            'paywall',
            'subscription required',
            'subscribe to continue',
            'premium content',
            'members only',
            'sign in to read',
            'create account to read',
            'free articles remaining',
            'you have reached your',
            'subscribe now',
            'become a member',
            'unlock this article',
        ]
        
        # Check HTML text
        html_lower = html.lower()
        for indicator in paywall_indicators:
            if indicator in html_lower:
                return True
        
        # Check for common paywall class names
        paywall_classes = [
            'paywall',
            'subscription-wall',
            'premium-content',
            'member-only',
            'article-locked',
        ]
        
        for class_name in paywall_classes:
            if soup.find(class_=re.compile(class_name, re.I)):
                return True
        
        return False
    
    def extract_article_content(self, html: str, url: str) -> Dict[str, str]:
        """
        Extract main header and article content from HTML
        
        Args:
            html: HTML content
            url: Source URL (for context)
            
        Returns:
            Dictionary with 'header', 'content', and 'paywall' status
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check for paywall
            is_paywalled = self.detect_paywall(html, soup)
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                script.decompose()
            
            article_data = {
                'header': '',
                'content': '',
                'url': url,
                'paywall': is_paywalled
            }
            
            if is_paywalled and self.debug:
                print(f"    ⚠ Paywall detected - will extract available preview content")
            
            # Try multiple strategies to find the main header
            header_selectors = [
                'h1',
                'article h1',
                'main h1',
                '.article-header h1',
                '.post-title h1',
                '.entry-title h1',
                '[role="main"] h1',
                'h1.article-title',
                'h1.post-title',
                'h1[data-testid]',  # For sites like Wired
                '.content-header h1',
                '.story-header h1',
            ]
            
            for selector in header_selectors:
                try:
                    header_elem = soup.select_one(selector)
                    if header_elem:
                        header_text = header_elem.get_text(strip=True)
                        if header_text and len(header_text) > 10:  # Valid header
                            article_data['header'] = header_text
                            if self.debug:
                                print(f"    Found header using: {selector}")
                            break
                except:
                    continue
            
            # If no header found, try to find any h1
            if not article_data['header']:
                h1 = soup.find('h1')
                if h1:
                    article_data['header'] = h1.get_text(strip=True)
                    if self.debug:
                        print(f"    Found header using fallback: h1")
            
            # Try multiple strategies to find article content
            # Expanded selectors for various news sites
            content_selectors = [
                'article',
                'main article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '[role="article"]',
                '.article-body',
                '.post-body',
                'main',
                '[itemprop="articleBody"]',
                '.story-body',  # Wired, New York Times
                '.article__body',  # Various news sites
                '.content-body',
                '.article-text',
                '[data-module="ArticleBody"]',  # Wired
                '.article__content',
                'div[class*="article"]',
                'div[class*="content"]',
                'div[class*="story"]',
            ]
            
            content_text = ""
            for selector in content_selectors:
                try:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        # Get all paragraphs - try both p tags and divs with text
                        paragraphs = content_elem.find_all(['p', 'div'])
                        text_parts = []
                        
                        for p in paragraphs:
                            # Skip if it has children that are block elements (likely containers)
                            if p.find(['div', 'section', 'article']):
                                continue
                            
                            text = p.get_text(strip=True)
                            # Filter out very short paragraphs (likely navigation, ads, etc.)
                            # Also filter out common non-content text
                            if (text and len(text) > 50 and 
                                not any(skip in text.lower() for skip in [
                                    'subscribe', 'newsletter', 'sign up', 'cookie',
                                    'privacy policy', 'terms of service', 'advertisement'
                                ])):
                                text_parts.append(text)
                        
                        if text_parts and len(text_parts) >= 1:  # Need at least 1 paragraph
                            content_text = '\n\n'.join(text_parts)
                            # Limit content length (first 10000 chars to get more content)
                            if len(content_text) > 10000:
                                content_text = content_text[:10000] + "... [truncated]"
                            if self.debug:
                                print(f"    ✓ Found content using: {selector} ({len(text_parts)} paragraphs, {len(content_text)} chars)")
                            break
                except Exception as e:
                    if self.debug:
                        print(f"    Error with selector {selector}: {e}")
                    continue
            
            # Fallback 1: Try extracting from main element directly
            if not content_text:
                main_elem = soup.find('main')
                if main_elem:
                    paragraphs = main_elem.find_all('p')
                    text_parts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 30:  # Lower threshold
                            text_parts.append(text)
                    
                    if text_parts:
                        content_text = '\n\n'.join(text_parts[:30])
                        if len(content_text) > 10000:
                            content_text = content_text[:10000] + "... [truncated]"
                        if self.debug:
                            print(f"    ✓ Found content using fallback: main ({len(text_parts)} paragraphs)")
            
            # Fallback 2: Try extracting from body if no specific content found
            if not content_text:
                body = soup.find('body')
                if body:
                    # Get all paragraphs from body, but be more selective
                    paragraphs = body.find_all('p')
                    text_parts = []
                    for p in paragraphs:
                        # Skip paragraphs in nav, footer, etc.
                        try:
                            parent = p.find_parent()
                            if parent:
                                parent_classes = ' '.join(parent.get('class', []))
                                if any(skip in parent_classes.lower() for skip in ['nav', 'footer', 'header', 'sidebar', 'ad', 'menu']):
                                    continue
                        except:
                            pass
                        
                        text = p.get_text(strip=True)
                        if text and len(text) > 30:  # Lower threshold
                            text_parts.append(text)
                    
                    if text_parts:
                        # Take the longest paragraphs (likely main content)
                        text_parts.sort(key=len, reverse=True)
                        content_text = '\n\n'.join(text_parts[:30])  # Top 30 paragraphs
                        if len(content_text) > 10000:
                            content_text = content_text[:10000] + "... [truncated]"
                        if self.debug:
                            print(f"    ✓ Found content using fallback: body ({len(text_parts)} paragraphs)")
            
            # Fallback 3: Try extracting from any div with substantial text
            if not content_text:
                all_divs = soup.find_all('div')
                best_div = None
                best_text_length = 0
                
                for div in all_divs:
                    # Skip if it's likely a container/navigation
                    div_classes = ' '.join(div.get('class', []))
                    if any(skip in div_classes.lower() for skip in ['nav', 'footer', 'header', 'sidebar', 'ad', 'menu', 'widget']):
                        continue
                    
                    # Get all text from this div
                    div_text = div.get_text(strip=True)
                    if len(div_text) > best_text_length and len(div_text) > 200:
                        # Check if it has multiple paragraphs
                        paragraphs = div.find_all('p')
                        if len(paragraphs) >= 2:
                            best_div = div
                            best_text_length = len(div_text)
                
                if best_div:
                    paragraphs = best_div.find_all('p')
                    text_parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 30]
                    if text_parts:
                        content_text = '\n\n'.join(text_parts[:30])
                        if len(content_text) > 10000:
                            content_text = content_text[:10000] + "... [truncated]"
                        if self.debug:
                            print(f"    ✓ Found content using fallback: best div ({len(text_parts)} paragraphs)")
            
            article_data['content'] = content_text
            
            if not content_text and self.debug:
                print(f"    ⚠ Could not extract content from: {url}")
                # Debug: show what elements we have
                h1_count = len(soup.find_all('h1'))
                p_count = len(soup.find_all('p'))
                article_count = len(soup.find_all('article'))
                main_count = len(soup.find_all('main'))
                print(f"      Debug: Found {h1_count} h1, {p_count} p, {article_count} article, {main_count} main elements")
            
            return article_data
            
        except Exception as e:
            if self.debug:
                print(f"    ✗ Error extracting content: {e}")
            return {
                'header': '',
                'content': '',
                'url': url
            }
    
    def process_articles(self, name: str, top_n: int = 5) -> List[Dict]:
        """
        Search for articles, download, and extract content
        
        Args:
            name: Person's name
            top_n: Number of articles to process (default: 5)
            
        Returns:
            List of article dictionaries with header, content, and url
        """
        articles = []
        
        # Step 1: Search for articles
        if self.debug:
            print(f"\n{'='*60}")
            print(f"Searching for articles about: {name}")
            print(f"{'='*60}\n")
        
        article_urls = self.search_articles(name, top_n=top_n)
        
        if not article_urls:
            if self.debug:
                print("  ⚠ No articles found")
            return articles
        
        # Step 2: Download and extract content from each article
        if self.debug:
            print(f"\nProcessing {len(article_urls)} articles...\n")
        
        for i, url in enumerate(article_urls, 1):
            if self.debug:
                print(f"Article {i}/{len(article_urls)}:")
            
            # Download HTML
            html = self.download_article_html(url)
            if not html:
                continue
            
            # Extract content
            article_data = self.extract_article_content(html, url)
            
            if article_data.get('content') or article_data.get('header'):
                articles.append(article_data)
                header_preview = article_data.get('header', 'No header')[:60]
                content_length = len(article_data.get('content', ''))
                paywall_status = " [PAYWALL]" if article_data.get('paywall') else ""
                if self.debug:
                    print(f"    ✓ Extracted: {header_preview}... ({content_length} chars){paywall_status}")
            else:
                if self.debug:
                    paywall_status = " (paywalled)" if article_data.get('paywall') else ""
                    print(f"    ⚠ Could not extract content{paywall_status} - skipping article")
            
            # Small delay between requests
            time.sleep(1)
        
        if self.debug:
            print(f"\n✓ Successfully processed {len(articles)}/{len(article_urls)} articles")
        
        return articles
    
    def save_articles_to_file(self, articles: List[Dict], output_file: str, name: str = ""):
        """
        Save articles to a text file
        
        Args:
            articles: List of article dictionaries
            output_file: Path to output file
            name: Person's name (for header)
        """
        if not articles:
            if self.debug:
                print("  ⚠ No articles to save")
            return
        
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("=" * 80 + "\n")
                if name:
                    f.write(f"Articles about: {name}\n")
                f.write(f"Extracted: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total articles: {len(articles)}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write each article
                for i, article in enumerate(articles, 1):
                    f.write(f"ARTICLE {i}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"URL: {article['url']}\n")
                    if article.get('paywall'):
                        f.write(f"PAYWALL: Yes (preview content only)\n")
                    if article.get('header'):
                        f.write(f"\nHEADER:\n{article['header']}\n")
                    f.write(f"\nCONTENT:\n{article.get('content', 'No content extracted')}\n")
                    f.write("\n" + "=" * 80 + "\n\n")
            
            if self.debug:
                print(f"  ✓ Saved {len(articles)} articles to: {output_file}")
                
        except Exception as e:
            print(f"  ✗ Error saving articles: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("Article Search Module (SERP API)")
    print("=" * 60)
    
    searcher = ArticleSearcher(debug=True)
    
    # Get name from command line or prompt
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
    else:
        name = input("\nEnter a name to search for articles: ").strip()
    
    if not name:
        print("❌ No name provided")
        sys.exit(1)
    
    # Process articles
    articles = searcher.process_articles(name, top_n=5)
    
    if articles:
        # Display summary
        print("\n" + "=" * 60)
        print("ARTICLES FOUND")
        print("=" * 60)
        for i, article in enumerate(articles, 1):
            print(f"\nArticle {i}:")
            print(f"  URL: {article['url']}")
            if article.get('header'):
                header_preview = article['header'][:80] + "..." if len(article['header']) > 80 else article['header']
                print(f"  Header: {header_preview}")
            content_length = len(article.get('content', ''))
            print(f"  Content: {content_length} characters")
        
        # Save to file
        print("\n" + "=" * 60)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(backend_dir, "data")
        output_file = os.path.join(data_dir, f"articles_{name.replace(' ', '_').lower()}.txt")
        searcher.save_articles_to_file(articles, output_file, name)
        
        print("\n✓ Article search complete!")
    else:
        print("\n⚠ No articles found or extracted")

