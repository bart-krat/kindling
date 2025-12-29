import os
import requests
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables - specify the path explicitly
load_dotenv(dotenv_path='.env')  # Make sure it's loading from backend/.env


class TwitterScraper:
    def __init__(self, debug=False):
        """
        Initialize Twitter API client with OAuth 2.0 Bearer Token authentication
        
        OAuth 2.0 Bearer Token (App-only) is used for automated backend scripts.
        This requires only the Bearer Token from your Twitter Developer Portal.
        """
        # Get OAuth 2.0 Bearer Token (required for OAuth 2.0 authentication)
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        if debug:
            print("\n=== OAuth 2.0 Token Verification ===")
            print(f"Bearer Token (OAuth 2.0) loaded: {'Yes' if self.bearer_token else 'No'} (length: {len(self.bearer_token) if self.bearer_token else 0})")
            if self.bearer_token:
                print(f"Bearer Token preview: {self.bearer_token[:10]}...{self.bearer_token[-4:]}")
            print("=" * 30 + "\n")
        
        # Validate that we have Bearer Token (required for OAuth 2.0)
        if not self.bearer_token:
            raise ValueError(
                "Missing Twitter OAuth 2.0 Bearer Token. Please ensure TWITTER_BEARER_TOKEN "
                "is set in your .env file.\n\n"
                "To get your Bearer Token:\n"
                "1. Go to https://developer.twitter.com/en/portal/dashboard\n"
                "2. Click on your app\n"
                "3. Go to 'Keys and tokens' tab\n"
                "4. Under 'Bearer Token', click 'Regenerate'\n"
                "5. Copy the token and add it to your .env file as TWITTER_BEARER_TOKEN"
            )
        
        self.debug = debug
        
        if debug:
            print("Initialized with OAuth 2.0 Bearer Token (Direct API calls)")
    
    def test_bearer_token_direct(self) -> bool:
        """
        Test Bearer Token by making a direct API call
        Returns True if token works, False otherwise
        """
        if not self.bearer_token:
            print("  ✗ No Bearer Token available")
            return False
        
        try:
            print("  Testing Bearer Token with direct API call...")
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            # Use a well-known active account for testing
            url = "https://api.twitter.com/2/users/by/username/elonmusk"
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"  Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    print(f"  ✓ Bearer Token is valid!")
                    print(f"    Successfully fetched: @{data['data'].get('username')} (ID: {data['data'].get('id')})")
                    return True
                elif 'errors' in data:
                    # Check if it's an authentication error or just a user issue
                    error = data['errors'][0] if data['errors'] else {}
                    error_type = error.get('type', '')
                    if 'unauthorized' in error_type.lower() or 'forbidden' in error_type.lower():
                        print(f"  ✗ Bearer Token authentication failed")
                        print(f"    Error: {error.get('detail', 'Unknown error')}")
                        return False
                    else:
                        # Token is valid, but user has an issue (suspended, not found, etc.)
                        print(f"  ✓ Bearer Token is valid! (User issue: {error.get('detail', 'Unknown')})")
                        return True
                else:
                    print(f"  ✗ Unexpected response format: {data}")
                    return False
            elif response.status_code == 401:
                print(f"  ✗ Bearer Token authentication failed: HTTP 401 Unauthorized")
                try:
                    error_data = response.json()
                    print(f"  Error: {error_data}")
                except:
                    print(f"  Response text: {response.text[:200]}")
                return False
            else:
                print(f"  ✗ Bearer Token test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"  Error response: {error_data}")
                except:
                    print(f"  Response text: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"  ✗ Direct API test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_auth(self) -> bool:
        """
        Test OAuth 2.0 authentication by making a simple API call
        Returns True if auth works, False otherwise
        """
        try:
            print("  Testing OAuth 2.0 Bearer Token with direct API call...")
            print("  (Note: Bearer Token is app-only, so we can't get 'me' info)")
            
            # Test by getting a well-known active user account
            print("  Attempting to fetch @elonmusk user...")
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            url = "https://api.twitter.com/2/users/by/username/elonmusk"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    print(f"  ✓ OAuth 2.0 authentication successful!")
                    print(f"    Successfully fetched @{data['data'].get('username')} (ID: {data['data'].get('id')})")
                    return True
                elif 'errors' in data:
                    error = data['errors'][0] if data['errors'] else {}
                    if 'suspended' in str(error).lower() or 'not found' in str(error).lower():
                        print(f"  ✓ Bearer Token is valid! (User issue: {error.get('detail', 'Unknown')})")
                        return True
            elif response.status_code == 401:
                print(f"  ✗ OAuth 2.0 authentication failed: 401 Unauthorized")
                try:
                    error_data = response.json()
                    print(f"    Error: {error_data}")
                except:
                    print(f"    Response: {response.text[:200]}")
                return False
            else:
                print(f"  ✗ Authentication test failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Authentication test failed with unexpected error: {type(e).__name__}")
            print(f"    Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_user_posts_by_id(self, user_id: str, max_results: int = 100) -> List[Dict]:
        """
        Get posts (tweets) from a specific user by their user ID using direct API call
        
        Args:
            user_id: Twitter user ID (as string)
            max_results: Maximum number of posts to retrieve (max 100 per request)
            
        Returns:
            List of post dictionaries with id, text, created_at, and metrics
        """
        if self.debug:
            print(f"Fetching tweets for user ID {user_id}...")
        
        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            
            # Build the API URL with query parameters
            url = f"https://api.twitter.com/2/users/{user_id}/tweets"
            params = {
                'max_results': min(max_results, 100),  # API limit is 100 per request
                'tweet.fields': 'created_at,public_metrics,text,edit_history_tweet_ids'
            }
            
            if self.debug:
                print(f"  Making API request to: {url}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data:
                    posts = []
                    for tweet in data['data']:
                        posts.append({
                            'id': tweet.get('id'),
                            'text': tweet.get('text'),
                            'created_at': tweet.get('created_at'),
                            'edit_history_tweet_ids': tweet.get('edit_history_tweet_ids', []),
                            'metrics': tweet.get('public_metrics', {})
                        })
                    
                    if self.debug:
                        print(f"  ✓ Successfully fetched {len(posts)} tweet(s)")
                    return posts
                else:
                    if self.debug:
                        print("  ⚠ No tweets returned (user may have no tweets or they're private)")
                    return []
                    
            elif response.status_code == 401:
                print(f"  ✗ OAuth 2.0 authentication failed: 401 Unauthorized")
                try:
                    error_data = response.json()
                    print(f"     Error: {error_data}")
                except:
                    print(f"     Response: {response.text[:200]}")
                return []
            elif response.status_code == 404:
                print(f"  ✗ User ID {user_id} not found")
                return []
            elif response.status_code == 403:
                print(f"  ✗ Forbidden: User's tweets may be private or protected")
                return []
            else:
                print(f"  ✗ Unexpected error: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"     Error: {error_data}")
                except:
                    print(f"     Response: {response.text[:200]}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"  ✗ Request timeout")
            return []
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_tweets_to_file(self, tweets: List[Dict], output_file: str, format: str = 'text'):
        """
        Save tweet texts to a file
        
        Args:
            tweets: List of tweet dictionaries
            output_file: Path to output file
            format: Output format - 'text' (one per line) or 'json' (JSON lines)
        """
        if not tweets:
            print(f"  ⚠ No tweets to save")
            return
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            if format == 'text':
                # Save as plain text, one tweet per line
                with open(output_file, 'w', encoding='utf-8') as f:
                    for tweet in tweets:
                        text = tweet.get('text', '').strip()
                        if text:
                            # Replace newlines with spaces for single-line format
                            text_clean = ' '.join(text.split())
                            f.write(text_clean + '\n')
                
                if self.debug:
                    print(f"  ✓ Saved {len(tweets)} tweet(s) to {output_file} (text format)")
            
            elif format == 'json':
                # Save as JSON lines (one JSON object per line)
                with open(output_file, 'w', encoding='utf-8') as f:
                    for tweet in tweets:
                        f.write(json.dumps(tweet, ensure_ascii=False) + '\n')
                
                if self.debug:
                    print(f"  ✓ Saved {len(tweets)} tweet(s) to {output_file} (JSON lines format)")
            
            else:
                raise ValueError(f"Unknown format: {format}. Use 'text' or 'json'")
                
        except Exception as e:
            print(f"  ✗ Error saving to file: {e}")
            import traceback
            traceback.print_exc()
    
    def get_user_posts(self, username: str, max_results: int = 100) -> List[Dict]:
        """
        Get posts (tweets) from a specific user by username
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum number of posts to retrieve (max 100 per request)
            
        Returns:
            List of post dictionaries with id, text, created_at, and metrics
        """
        try:
            # Remove @ if present
            username = username.lstrip('@')
            
            if self.debug:
                print(f"Looking up user: @{username}")
            
            # Get user ID from username using direct API call
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            url = f"https://api.twitter.com/2/users/by/username/{username}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Error: User @{username} not found (HTTP {response.status_code})")
                return []
            
            data = response.json()
            if 'data' not in data:
                print(f"Error: User @{username} not found")
                return []
            
            user_id = data['data']['id']
            if self.debug:
                print(f"✓ Found user @{username} with ID: {user_id}")
            
            # Use the ID-based method
            return self.get_user_posts_by_id(str(user_id), max_results)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user info: {e}")
            return []
        except Exception as e:
            print(f"Error fetching tweets: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_user_id(self, username: str) -> Optional[str]:
        """
        Get user ID from username using direct API call
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            User ID as string or None
        """
        username = username.lstrip('@')
        
        try:
            if self.debug:
                print(f"  Getting user ID for @{username}...")
            
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            url = f"https://api.twitter.com/2/users/by/username/{username}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'id' in data['data']:
                    user_id = str(data['data']['id'])
                    if self.debug:
                        print(f"  ✓ Found user ID: {user_id}")
                    return user_id
            else:
                if self.debug:
                    print(f"  ✗ Failed: HTTP {response.status_code}")
                return None
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error: {e}")
            return None
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        Get user information using direct API call
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            Dictionary with user information or None
        """
        try:
            username = username.lstrip('@')
            
            if self.debug:
                print(f"Attempting to get user info for @{username}...")
            
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            
            # Get user info with additional fields
            url = f"https://api.twitter.com/2/users/by/username/{username}"
            params = {
                'user.fields': 'description,public_metrics,created_at'
            }
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    user_data = data['data']
                    return {
                        'id': user_data.get('id'),
                        'username': user_data.get('username'),
                        'name': user_data.get('name'),
                        'description': user_data.get('description'),
                        'created_at': user_data.get('created_at'),
                        'metrics': user_data.get('public_metrics', {})
                    }
            
            return None
        except Exception as e:
            if self.debug:
                print(f"Error fetching user info: {e}")
            return None


if __name__ == "__main__":
    # Test the scraper with debugging enabled
    print("\n" + "=" * 50)
    print("Twitter API OAuth 2.0 Authentication Test")
    print("=" * 50)
    
    scraper = TwitterScraper(debug=True)
    
    # Step 1: Test OAuth 2.0 authentication
    print("\nStep 1: Testing OAuth 2.0 Bearer Token authentication...")
    print("(Testing with two methods to verify token validity)\n")
    
    # Test authentication with direct API calls
    direct_test = scraper.test_bearer_token_direct()
    print()
    
    # Also test with the alternative method
    api_test = scraper.test_auth()
    
    # Both should work, but we'll proceed if at least one works
    auth_works = direct_test or api_test
    
    if not auth_works:
        print("\n❌ OAuth 2.0 authentication failed with both methods.")
        print("Please check your Bearer Token and app settings.\n")
        print("Troubleshooting:")
        print("1. Verify your .env file is in the backend/ directory")
        print("2. Check that TWITTER_BEARER_TOKEN is set correctly:")
        print("   - No extra spaces before/after the token")
        print("   - Token should be ~114 characters long")
        print("   - Token should start with 'AAAAAAAAAA'")
        print("3. Get/regenerate Bearer Token in Twitter Developer Portal:")
        print("   - Go to https://developer.twitter.com/en/portal/dashboard")
        print("   - Click on your app → 'Keys and tokens' tab")
        print("   - Under 'Bearer Token', click 'Regenerate'")
        print("   - Copy the ENTIRE token immediately (shown only once)")
        print("   - Add to .env as: TWITTER_BEARER_TOKEN=your_token_here")
        print("4. Verify your app has 'Read' permissions:")
        print("   - Go to Settings → User authentication settings")
        print("   - Under 'App permissions', ensure it's 'Read' or 'Read and Write'")
        print("5. Ensure app type is 'Automated App' or 'Bot'")
        print("6. After changing permissions, regenerate Bearer Token")
        exit(1)
    else:
        print("\n✓ OAuth 2.0 authentication verified!")
    
    # Step 2: Get user posts by ID (direct API method)
    print("\nStep 2: Fetching tweets from user ID...")
    user_id = "41777199"  # @getpeid user ID - change this to test different users
    print(f"Using user ID: {user_id}")
    
    posts = scraper.get_user_posts_by_id(user_id, max_results=10)
    
    if posts:
        print(f"\n✓ SUCCESS! Found {len(posts)} tweet(s):\n")
        
        # Display first few tweets
        display_count = min(3, len(posts))
        for i, post in enumerate(posts[:display_count], 1):
            print(f"Tweet {i}:")
            print(f"  ID: {post['id']}")
            print(f"  Text: {post['text'][:150]}..." if len(post['text']) > 150 else f"  Text: {post['text']}")
            print(f"  Created: {post['created_at']}")
            metrics = post.get('metrics', {})
            print(f"  Likes: {metrics.get('like_count', 0)}, Retweets: {metrics.get('retweet_count', 0)}")
            print()
        
        if len(posts) > display_count:
            print(f"... and {len(posts) - display_count} more tweet(s)\n")
        
        # Step 3: Save tweets to file
        print("Step 3: Saving tweets to file...")
        output_file = f"tweets_{user_id}.txt"
        scraper.save_tweets_to_file(posts, output_file, format='text')
        
        print(f"\n✓ All done! Tweets saved to: {output_file}")
        print(f"  File contains {len(posts)} tweet(s) ready for embedding processing")
    else:
        print("\n❌ No tweets found or error occurred")
        print("\nPossible reasons:")
        print("  - User has no tweets")
        print("  - Tweets are private/protected")
        print("  - User ID is incorrect")
        print("  - Rate limit exceeded (wait and try again)")