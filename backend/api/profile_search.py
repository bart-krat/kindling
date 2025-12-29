import os
import re
import requests
from typing import Dict, Optional, List
from dotenv import load_dotenv
from urllib.parse import quote_plus, unquote
import time
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv(dotenv_path='.env')


class ProfileSearcher:
    def __init__(self, debug: bool = False):
        """
        Initialize profile searcher
        
        Args:
            debug: Print debug information
        """
        self.debug = debug
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Set up headers for web scraping (Google search) - more realistic
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        if debug:
            print("✓ ProfileSearcher initialized")
    
    def search_twitter_profile(self, name: str) -> Optional[Dict]:
        """
        Search for Twitter/X profile by name using Google search
        
        Args:
            name: Person's name to search for
            
        Returns:
            Dictionary with 'url' and all found URLs from Google search
        """
        try:
            if self.debug:
                print(f"  Searching Twitter/X for: {name}")
            
            # Use Google search to find Twitter profile
            query = f'"{name}" (twitter OR "x.com")'
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            
            response = requests.get(search_url, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                html = response.text
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Method 1: Look for links in search results
                links = soup.find_all('a', href=True)
                all_matches = []
                
                for link in links:
                    href = link.get('href', '')
                    if 'twitter.com/' in href or 'x.com/' in href:
                        # Clean up Google's redirect URLs
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        elif href.startswith('/url?'):
                            continue
                        
                        if href.startswith('http') and ('twitter.com/' in href or 'x.com/' in href):
                            all_matches.append(href)
                
                # Method 2: Also search in raw HTML text
                twitter_patterns = [
                    r'https?://(?:www\.)?twitter\.com/[\w]+',
                    r'https?://(?:www\.)?x\.com/[\w]+'
                ]
                
                for pattern in twitter_patterns:
                    text_matches = re.findall(pattern, html)
                    all_matches.extend(text_matches)
                
                if all_matches:
                    # Clean and deduplicate URLs
                    unique_matches = []
                    seen = set()
                    for match in all_matches:
                        # Normalize x.com to twitter.com
                        normalized = match.replace('x.com', 'twitter.com')
                        # Remove query parameters
                        clean_url = normalized.split('?')[0].split('#')[0].rstrip('/')
                        # Filter out non-profile URLs
                        if (clean_url not in seen and 
                            ('twitter.com/' in clean_url) and
                            not any(excluded in clean_url for excluded in ['/status/', '/i/', '/hashtag/', '/search'])):
                            unique_matches.append(clean_url)
                            seen.add(clean_url)
                    
                    if unique_matches:
                        result = {
                            'url': unique_matches[0],
                            'all_urls': unique_matches
                        }
                        
                        if self.debug:
                            print(f"  ✓ Found {len(unique_matches)} Twitter/X profile(s): {unique_matches[0]}")
                        
                        return result
                
                if self.debug:
                    print(f"  ⚠ No Twitter/X profile URL found for: {name}")
                return None
            else:
                if self.debug:
                    print(f"  ✗ Google search error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching Twitter: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def search_linkedin_profile(self, name: str) -> Optional[Dict]:
        """
        Search for LinkedIn profile using Google search
        
        Args:
            name: Person's name to search for
            
        Returns:
            Dictionary with 'url' and all found URLs from Google search
        """
        try:
            if self.debug:
                print(f"  Searching LinkedIn for: {name}")
            
            # Google search query for LinkedIn profile
            query = f"{name} linkedin"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            
            response = requests.get(search_url, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                html = response.text
                
                # Parse HTML with BeautifulSoup for better extraction
                soup = BeautifulSoup(html, 'html.parser')
                
                # Method 1: Look for links in search results
                links = soup.find_all('a', href=True)
                matches = []
                
                for link in links:
                    href = link.get('href', '')
                    # Extract URLs from href attributes
                    if 'linkedin.com/in/' in href:
                        # Clean up Google's redirect URLs
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        elif href.startswith('/url?'):
                            continue
                        
                        if href.startswith('http') and 'linkedin.com/in/' in href:
                            matches.append(href)
                
                # Method 2: Also search in raw HTML text (fallback)
                linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/[\w-]+'
                text_matches = re.findall(linkedin_pattern, html)
                matches.extend(text_matches)
                
                if matches:
                    # Clean and deduplicate URLs
                    unique_matches = []
                    seen = set()
                    for match in matches:
                        # Normalize URL
                        if not match.startswith('http'):
                            match = 'https://' + match
                        # Remove query parameters
                        clean_url = match.split('?')[0].split('#')[0].rstrip('/')
                        if clean_url not in seen and 'linkedin.com/in/' in clean_url:
                            unique_matches.append(clean_url)
                            seen.add(clean_url)
                    
                    if unique_matches:
                        result = {
                            'url': unique_matches[0],
                            'all_urls': unique_matches
                        }
                        
                        if self.debug:
                            print(f"  ✓ Found {len(unique_matches)} LinkedIn profile(s): {unique_matches[0]}")
                        
                        return result
                
                if self.debug:
                    print(f"  ⚠ No LinkedIn profile found for: {name}")
                    # Debug: Check if we got a response
                    if 'captcha' in html.lower() or 'blocked' in html.lower():
                        print(f"    (Google may be blocking the request)")
                return None
            else:
                if self.debug:
                    print(f"  ✗ Google search error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching LinkedIn: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def search_instagram_profile(self, name: str) -> Optional[Dict]:
        """
        Search for Instagram profile using Google search
        
        Args:
            name: Person's name to search for
            
        Returns:
            Dictionary with 'url' and all found URLs from Google search
        """
        try:
            if self.debug:
                print(f"  Searching Instagram for: {name}")
            
            # Google search query for Instagram profile
            query = f'"{name}" instagram'
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            
            response = requests.get(search_url, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                html = response.text
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Method 1: Look for links in search results
                links = soup.find_all('a', href=True)
                matches = []
                
                for link in links:
                    href = link.get('href', '')
                    if 'instagram.com/' in href:
                        # Clean up Google's redirect URLs
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        elif href.startswith('/url?'):
                            continue
                        
                        if href.startswith('http') and 'instagram.com/' in href:
                            matches.append(href)
                
                # Method 2: Also search in raw HTML text
                instagram_pattern = r'https?://(?:www\.)?instagram\.com/[\w.]+'
                text_matches = re.findall(instagram_pattern, html)
                matches.extend(text_matches)
                
                if matches:
                    # Clean and deduplicate URLs
                    unique_matches = []
                    seen = set()
                    for match in matches:
                        # Remove query parameters
                        clean_url = match.split('?')[0].split('#')[0].rstrip('/')
                        # Filter out non-profile URLs
                        if (clean_url not in seen and 
                            'instagram.com/' in clean_url and
                            not any(excluded in clean_url for excluded in ['/p/', '/reel/', '/tv/', '/explore/', '/accounts/', '/direct/'])):
                            unique_matches.append(clean_url)
                            seen.add(clean_url)
                    
                    if unique_matches:
                        result = {
                            'url': unique_matches[0],
                            'all_urls': unique_matches
                        }
                        
                        if self.debug:
                            print(f"  ✓ Found {len(unique_matches)} Instagram profile(s): {unique_matches[0]}")
                        
                        return result
                
                if self.debug:
                    print(f"  ⚠ No Instagram profile found for: {name}")
                return None
            else:
                if self.debug:
                    print(f"  ✗ Google search error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching Instagram: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def search_all_profiles(self, name: str) -> Dict:
        """
        Search for all profiles (LinkedIn, Twitter, Instagram) for a given name
        
        Args:
            name: Person's name to search for
            
        Returns:
            Dictionary with 'name', 'linkedin', 'twitter', 'instagram'
        """
        if self.debug:
            print(f"\n{'='*60}")
            print(f"Searching profiles for: {name}")
            print(f"{'='*60}\n")
        
        results = {
            'name': name,
            'linkedin': None,
            'twitter': None,
            'instagram': None
        }
        
        # Search LinkedIn
        linkedin_result = self.search_linkedin_profile(name)
        if linkedin_result:
            results['linkedin'] = {
                'profile_url': linkedin_result['url'],
                'all_urls': linkedin_result.get('all_urls', [])
            }
        
        # Small delay between searches
        time.sleep(1)
        
        # Search Twitter
        twitter_result = self.search_twitter_profile(name)
        if twitter_result:
            results['twitter'] = {
                'profile_url': twitter_result['url'],
                'all_urls': twitter_result.get('all_urls', [])
            }
        
        # Small delay between searches
        time.sleep(1)
        
        # Search Instagram
        instagram_result = self.search_instagram_profile(name)
        if instagram_result:
            results['instagram'] = {
                'profile_url': instagram_result['url'],
                'all_urls': instagram_result.get('all_urls', [])
            }
        
        return results
    
    def save_results(self, results: Dict, output_file: str):
        """
        Save search results to a JSON file
        
        Args:
            results: Results dictionary from search_all_profiles
            output_file: Path to output file
        """
        import json
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            if self.debug:
                print(f"\n✓ Results saved to: {output_file}")
                
        except Exception as e:
            print(f"✗ Error saving results: {e}")


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("Profile Search Module")
    print("=" * 60)
    
    searcher = ProfileSearcher(debug=True)
    
    # Get name from command line or prompt
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
    else:
        name = input("\nEnter a name to search: ").strip()
    
    if not name:
        print("❌ No name provided")
        sys.exit(1)
    
    # Search for all profiles
    results = searcher.search_all_profiles(name)
    
    # Display results
    print("\n" + "=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)
    print(f"\nName: {results['name']}\n")
    
    if results['linkedin']:
        print("LinkedIn:")
        print(f"  Primary URL: {results['linkedin']['profile_url']}")
        if results['linkedin'].get('all_urls') and len(results['linkedin']['all_urls']) > 1:
            print(f"  All URLs found: {len(results['linkedin']['all_urls'])}")
            for i, url in enumerate(results['linkedin']['all_urls'][:5], 1):  # Show first 5
                print(f"    {i}. {url}")
    else:
        print("LinkedIn: Not found")
    
    print()
    
    if results['twitter']:
        print("Twitter/X:")
        print(f"  Primary URL: {results['twitter']['profile_url']}")
        if results['twitter'].get('all_urls') and len(results['twitter']['all_urls']) > 1:
            print(f"  All URLs found: {len(results['twitter']['all_urls'])}")
            for i, url in enumerate(results['twitter']['all_urls'][:5], 1):  # Show first 5
                print(f"    {i}. {url}")
    else:
        print("Twitter/X: Not found")
    
    print()
    
    if results['instagram']:
        print("Instagram:")
        print(f"  Primary URL: {results['instagram']['profile_url']}")
        if results['instagram'].get('all_urls') and len(results['instagram']['all_urls']) > 1:
            print(f"  All URLs found: {len(results['instagram']['all_urls'])}")
            for i, url in enumerate(results['instagram']['all_urls'][:5], 1):  # Show first 5
                print(f"    {i}. {url}")
    else:
        print("Instagram: Not found")
    
    # Save results
    print("\n" + "=" * 60)
    output_file = f"data/profile_search_{name.replace(' ', '_').lower()}.json"
    searcher.save_results(results, output_file)
    
    print("\n✓ Search complete!")

