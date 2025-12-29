import os
import re
import json
import requests
import base64
from typing import Dict, Optional, List
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(dotenv_path='.env')


class SERPProfileSearcher:
    def __init__(self, debug: bool = False):
        """
        Initialize profile searcher using DataForSEO SERP API
        
        Args:
            debug: Print debug information
        """
        self.debug = debug
        
        # Get DataForSEO credentials
        self.login = os.getenv('DATAFORSEO_LOGIN')
        self.password = os.getenv('DATAFORSEO_PASSWORD')
        
        if not self.login or not self.password:
            raise ValueError(
                "DataForSEO credentials required. Set DATAFORSEO_LOGIN and "
                "DATAFORSEO_PASSWORD in .env file"
            )
        
        # Base URL for DataForSEO API
        self.base_url = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
        
        # Create basic auth header
        credentials = f"{self.login}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        if debug:
            print("✓ SERPProfileSearcher initialized with DataForSEO API")

        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        if debug:
            print("✓ SERPProfileSearcher initialized with DataForSEO API")
            if self.bearer_token:
                print("  Twitter Bearer Token loaded for user ID lookup")
    
    
    def search_google(self, query: str, location_code: int = 2826, language_code: str = "en", depth: int = 1) -> Optional[Dict]:
        """
        Search Google using DataForSEO SERP API
        
        Args:
            query: Search query
            location_code: Location code (2826 = United States)
            language_code: Language code (en = English)
            depth: Number of results pages (1 = first page only, sufficient for top results)
            
        Returns:
            API response dictionary or None
        """
        try:
            if self.debug:
                print(f"  Searching Google: {query}")
            
            payload = [
                {
                    "keyword": query,
                    "location_code": location_code,
                    "language_code": language_code,
                    "depth": depth,
                    "device": "desktop",
                    "os": "windows"
                }
            ]
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
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
                                print(f"  ✓ Found {result['items_count']} results")
                
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
    
    def extract_urls_from_results(self, api_response: Dict, platform: str = None) -> List[str]:
        """
        Extract URLs from DataForSEO API response
        
        Args:
            api_response: API response dictionary
            platform: Filter by platform ('linkedin', 'twitter', 'instagram') or None for all
            
        Returns:
            List of URLs
        """
        urls = []
        
        try:
            if 'tasks' not in api_response:
                return urls
            
            for task in api_response['tasks']:
                if 'result' not in task:
                    continue
                
                for result_item in task['result']:
                    if 'items' not in result_item:
                        continue
                    
                    for item in result_item['items']:
                        if 'url' in item:
                            url = item['url']
                            
                            # Filter by platform if specified
                            if platform:
                                if platform == 'linkedin' and 'linkedin.com/in/' in url:
                                    urls.append(url)
                                elif platform == 'twitter' and ('twitter.com/' in url or 'x.com/' in url):
                                    # Normalize x.com to twitter.com
                                    url = url.replace('x.com', 'twitter.com')
                                    urls.append(url)
                                elif platform == 'instagram' and 'instagram.com/' in url:
                                    urls.append(url)
                            else:
                                urls.append(url)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in urls:
                # Clean URL
                clean_url = url.split('?')[0].split('#')[0].rstrip('/')
                if clean_url not in seen:
                    unique_urls.append(clean_url)
                    seen.add(clean_url)
            
            return unique_urls
            
        except Exception as e:
            if self.debug:
                print(f"  ⚠ Error extracting URLs: {e}")
            return []
    

    def extract_username_from_url(self, url: str) -> Optional[str]:
        """
        Extract username from Twitter/X profile URL
        
        Args:
            url: Twitter profile URL (e.g., https://twitter.com/elonmusk or https://x.com/elonmusk)
            
        Returns:
            Username string or None
        """
        try:
            # Handle both twitter.com and x.com URLs
            url = url.replace('x.com', 'twitter.com')
            
            # Extract username from URL pattern: twitter.com/username
            pattern = r'twitter\.com/([^/?]+)'
            match = re.search(pattern, url)
            
            if match:
                username = match.group(1)
                # Remove @ if present
                username = username.lstrip('@')
                return username
            return None
        except Exception as e:
            if self.debug:
                print(f"  ⚠ Error extracting username: {e}")
            return None
    
    def get_twitter_user_id(self, username: str) -> Optional[str]:
        """
        Get Twitter user ID from username using Twitter API
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            User ID string or None
        """
        if not self.bearer_token:
            if self.debug:
                print(f"  ⚠ Twitter Bearer Token not available, skipping user ID lookup")
            return None
        
        try:
            username = username.lstrip('@')
            
            if self.debug:
                print(f"    Looking up user ID for @{username}...")
            
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            url = f"https://api.x.com/2/users/by/username/{username}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'id' in data['data']:
                    user_id = str(data['data']['id'])
                    if self.debug:
                        print(f"    ✓ Found user ID: {user_id}")
                    return user_id
            else:
                if self.debug:
                    print(f"    ✗ API error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"    ✗ Error getting user ID: {e}")
            return None

    def search_linkedin_profile(self, name: str, top_n: int = 2) -> Optional[Dict]:
        """
        Search for LinkedIn profile using DataForSEO SERP API
        
        Args:
            name: Person's name to search for
            top_n: Number of top results to return (default: 2)
            
        Returns:
            Dictionary with 'url' and 'all_urls'
        """
        try:
            if self.debug:
                print(f"  Searching LinkedIn for: {name}")
            
            query = f"{name} linkedin"
            api_response = self.search_google(query, depth=1)
            
            if not api_response:
                return None
            
            urls = self.extract_urls_from_results(api_response, platform='linkedin')
            
            if urls:
                # Get top N results
                profile_urls = urls[:top_n]
                
                result = {
                    'url': profile_urls[0] if profile_urls else None,
                    'all_urls': profile_urls
                }
                
                if self.debug:
                    print(f"  ✓ Found {len(profile_urls)} LinkedIn profile(s): {profile_urls[0] if profile_urls else 'None'}")
                
                return result
            else:
                if self.debug:
                    print(f"  ⚠ No LinkedIn profiles found")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching LinkedIn: {e}")
            return None
    
    def search_twitter_profile(self, name: str, top_n: int = 2) -> Optional[Dict]:
        """
        Search for Twitter/X profile using DataForSEO SERP API, then get user ID from Twitter API
        
        Args:
            name: Person's name to search for
            top_n: Number of top results to return (default: 2)
            
        Returns:
            Dictionary with 'url', 'all_urls', 'username', and 'user_id'
        """
        try:
            if self.debug:
                print(f"  Searching Twitter/X for: {name}")
            
            query = f'"{name}" (twitter OR "x.com")'
            api_response = self.search_google(query, depth=1)
            
            if not api_response:
                return None
            
            urls = self.extract_urls_from_results(api_response, platform='twitter')
            
            if urls:
                # Filter out non-profile URLs and get top N
                profile_urls = [
                    url for url in urls 
                    if not any(excluded in url for excluded in ['/status/', '/i/', '/hashtag/', '/search'])
                ]
                # Remove duplicates
                profile_urls = list(dict.fromkeys(profile_urls))
                profile_urls = profile_urls[:top_n]
                
                # Extract username from primary URL and get user ID
                username = None
                user_id = None
                
                if profile_urls:
                    username = self.extract_username_from_url(profile_urls[0])
                    if username:
                        user_id = self.get_twitter_user_id(username)
                
                result = {
                    'url': profile_urls[0] if profile_urls else None,
                    'all_urls': profile_urls,
                    'username': username,
                    'user_id': user_id
                }
                
                if self.debug:
                    print(f"  ✓ Found {len(profile_urls)} Twitter/X profile(s): {profile_urls[0] if profile_urls else 'None'}")
                    if username:
                        print(f"    Username: @{username}")
                    if user_id:
                        print(f"    User ID: {user_id}")
                
                return result
            else:
                if self.debug:
                    print(f"  ⚠ No Twitter/X profiles found")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching Twitter: {e}")
            return None
    
    def search_instagram_profile(self, name: str, top_n: int = 2) -> Optional[Dict]:
        """
        Search for Instagram profile using DataForSEO SERP API
        
        Args:
            name: Person's name to search for
            top_n: Number of top results to return (default: 2)
            
        Returns:
            Dictionary with 'url' and 'all_urls'
        """
        try:
            if self.debug:
                print(f"  Searching Instagram for: {name}")
            
            query = f"{name} instagram"
            api_response = self.search_google(query, depth=1)
            
            if not api_response:
                if self.debug:
                    print(f"  ⚠ No API response for Instagram search")
                return None
            
            urls = self.extract_urls_from_results(api_response, platform='instagram')
            
            if urls:
                # Filter out non-profile URLs and get top N
                profile_urls = [
                    url for url in urls 
                    if not any(excluded in url for excluded in ['/p/', '/reel/', '/tv/', '/explore/', '/accounts/', '/direct/'])
                ]
                # Remove duplicates
                profile_urls = list(dict.fromkeys(profile_urls))
                profile_urls = profile_urls[:top_n]
                
                result = {
                    'url': profile_urls[0] if profile_urls else None,
                    'all_urls': profile_urls
                }
                
                if self.debug:
                    print(f"  ✓ Found {len(profile_urls)} Instagram profile(s): {profile_urls[0] if profile_urls else 'None'}")
                
                return result
            else:
                if self.debug:
                    print(f"  ⚠ No Instagram profiles found")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error searching Instagram: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def search_all_profiles(self, name: str, top_n: int = 2) -> Dict:
        """
        Search for all profiles (LinkedIn, Twitter, Instagram) using DataForSEO SERP API
        
        Args:
            name: Person's name to search for
            top_n: Number of top results to return for each platform (default: 2)
            
        Returns:
            Dictionary with 'name', 'linkedin', 'twitter', 'instagram' (with user_id for Twitter)
        """
        if self.debug:
            print(f"\n{'='*60}")
            print(f"Searching profiles for: {name} (using DataForSEO SERP API)")
            print(f"{'='*60}\n")
        
        results = {
            'name': name,
            'linkedin': None,
            'twitter': None,
            'instagram': None
        }
        
        # Search LinkedIn
        linkedin_result = self.search_linkedin_profile(name, top_n=top_n)
        if linkedin_result:
            results['linkedin'] = {
                'profile_url': linkedin_result['url'],
                'all_urls': linkedin_result.get('all_urls', [])
            }
        
        # Small delay between API calls
        time.sleep(1)
        
        # Search Twitter
        twitter_result = self.search_twitter_profile(name, top_n=top_n)
        if twitter_result:
            results['twitter'] = {
                'profile_url': twitter_result['url'],
                'all_urls': twitter_result.get('all_urls', []),
                'username': twitter_result.get('username'),
                'user_id': twitter_result.get('user_id')
            }
        
        # Small delay between API calls
        time.sleep(1)
        
        # Search Instagram
        instagram_result = self.search_instagram_profile(name, top_n=top_n)
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
    print("Profile Search Module (DataForSEO SERP API)")
    print("=" * 60)
    
    searcher = SERPProfileSearcher(debug=True)
    
    # Get name from command line or prompt
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
    else:
        name = input("\nEnter a name to search: ").strip()
    
    if not name:
        print("❌ No name provided")
        sys.exit(1)
    
    # Search for profiles (top 2 results for each)
    results = searcher.search_all_profiles(name, top_n=2)
    
    # Display results
    print("\n" + "=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)
    print(f"\nName: {results['name']}\n")
    
    if results['linkedin']:
        print("LinkedIn:")
        print(f"  Primary URL: {results['linkedin']['profile_url']}")
        if results['linkedin'].get('all_urls') and len(results['linkedin']['all_urls']) > 1:
            print(f"  All URLs found ({len(results['linkedin']['all_urls'])}):")
            for i, url in enumerate(results['linkedin']['all_urls'], 1):
                print(f"    {i}. {url}")
    else:
        print("LinkedIn: Not found")
    
    print()
    
    if results['twitter']:
        print("Twitter/X:")
        print(f"  Primary URL: {results['twitter']['profile_url']}")
        if results['twitter'].get('username'):
            print(f"  Username: @{results['twitter']['username']}")
        if results['twitter'].get('user_id'):
            print(f"  User ID: {results['twitter']['user_id']}")
        if results['twitter'].get('all_urls') and len(results['twitter']['all_urls']) > 1:
            print(f"  All URLs found ({len(results['twitter']['all_urls'])}):")
            for i, url in enumerate(results['twitter']['all_urls'], 1):
                print(f"    {i}. {url}")
    else:
        print("Twitter/X: Not found")
    
    print()
    
    if results['instagram']:
        print("Instagram:")
        print(f"  Primary URL: {results['instagram']['profile_url']}")
        if results['instagram'].get('all_urls') and len(results['instagram']['all_urls']) > 1:
            print(f"  All URLs found ({len(results['instagram']['all_urls'])}):")
            for i, url in enumerate(results['instagram']['all_urls'], 1):
                print(f"    {i}. {url}")
    else:
        print("Instagram: Not found")
    
    # Save results
    print("\n" + "=" * 60)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(backend_dir, "data")
    output_file = os.path.join(data_dir, f"profile_search_serp_{name.replace(' ', '_').lower()}.json")
    searcher.save_results(results, output_file)
    
    print("\n✓ Search complete!")