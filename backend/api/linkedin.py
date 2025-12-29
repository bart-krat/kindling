import os
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv(dotenv_path='.env')


class LinkedInScraper:
    def __init__(self, headless=False, debug=False):
        """
        Initialize LinkedIn scraper with Selenium
        
        Args:
            headless: Run browser in headless mode (no GUI)
            debug: Print debug information
        """
        self.debug = debug
        self.driver = None
        
        # Set up Chrome options
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Exclude automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            
            if debug:
                print("✓ Selenium WebDriver initialized successfully")
        except WebDriverException as e:
            raise RuntimeError(
                f"Failed to initialize Chrome WebDriver. Make sure ChromeDriver is installed.\n"
                f"Install with: brew install chromedriver (macOS) or download from https://chromedriver.chromium.org/\n"
                f"Error: {e}"
            )
    
    def login(self, email: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Login to LinkedIn
        
        Args:
            email: LinkedIn email (or use LINKEDIN_EMAIL from .env)
            password: LinkedIn password (or use LINKEDIN_PASSWORD from .env)
            
        Returns:
            True if login successful, False otherwise
        """
        # Get credentials from parameters or environment
        email = email or os.getenv('LINKEDIN_EMAIL')
        password = password or os.getenv('LINKEDIN_PASSWORD')
        
        if not email or not password:
            raise ValueError(
                "LinkedIn credentials required. Provide email/password as parameters "
                "or set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env file"
            )
        
        try:
            if self.debug:
                print("Navigating to LinkedIn login page...")
            
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter email
            if self.debug:
                print("Entering email...")
            email_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # Enter password
            if self.debug:
                print("Entering password...")
            password_input = self.driver.find_element(By.ID, "password")
            password_input.clear()
            password_input.send_keys(password)
            
            # Click login button
            if self.debug:
                print("Clicking login button...")
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete (check if we're redirected away from login page)
            time.sleep(3)
            
            # Check if login was successful
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                if self.debug:
                    print("✓ Login successful!")
                return True
            else:
                # Check for error messages
                try:
                    error_element = self.driver.find_element(By.CLASS_NAME, "alert-content")
                    error_text = error_element.text
                    if self.debug:
                        print(f"✗ Login failed: {error_text}")
                    return False
                except NoSuchElementException:
                    if self.debug:
                        print("✗ Login failed: Still on login page")
                    return False
                    
        except TimeoutException as e:
            if self.debug:
                print(f"✗ Login timeout: {e}")
            return False
        except Exception as e:
            if self.debug:
                print(f"✗ Login error: {e}")
            return False
    
    def get_user_posts(self, profile_url: str, max_posts: int = 10) -> List[Dict]:
        """
        Scrape posts from a LinkedIn profile
        
        Args:
            profile_url: Full LinkedIn profile URL (e.g., https://www.linkedin.com/in/username/)
            max_posts: Maximum number of posts to retrieve
            
        Returns:
            List of post dictionaries with text, timestamp, and metrics
        """
        if not self.driver:
            raise RuntimeError("WebDriver not initialized. Call __init__ first.")
        
        posts = []
        
        try:
            # Navigate directly to activity page instead of clicking
            # Convert profile URL to activity URL
            if '/recent-activity/' not in profile_url:
                if profile_url.endswith('/'):
                    activity_url = profile_url + "recent-activity/all/"
                else:
                    activity_url = profile_url + "/recent-activity/all/"
            else:
                activity_url = profile_url
            
            if self.debug:
                print(f"Navigating to activity page: {activity_url}")
            
            # Navigate directly to activity page
            self.driver.get(activity_url)
            time.sleep(5)  # Wait for initial page load
            
            # Wait for feed content to load
            try:
                # Wait for scrollable content container
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.scaffold-finite-scroll__content, div.scaffold-finite-scroll__content, main.scaffold-layout__main"))
                )
                if self.debug:
                    print("✓ Feed content container loaded")
                time.sleep(3)  # Additional wait for posts to render
            except TimeoutException:
                if self.debug:
                    print("⚠ Timeout waiting for feed content, continuing anyway...")
            
            # Debug: Print current state
            if self.debug:
                print(f"Current URL: {self.driver.current_url}")
                print(f"Page title: {self.driver.title}")
            
            # Find post elements - LinkedIn uses various class names
            # Try multiple selector strategies
            post_selectors = [
                "div.feed-shared-update-v2",
                "article.feed-shared-update-v2",
                "li.scaffold-finite-scroll__list-item",
                "div[data-urn*='activity']",
                "div.feed-shared-text-view",
                "div.update-components-text",
                "article[data-id*='urn']",
            ]
            
            post_elements = []
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        post_elements = elements
                        if self.debug:
                            print(f"✓ Found {len(elements)} potential posts using selector: {selector}")
                        break
                except Exception as e:
                    if self.debug:
                        print(f"  Selector '{selector}' failed: {e}")
                    continue
            
            # If no posts found with specific selectors, try more generic approach
            if not post_elements:
                if self.debug:
                    print("  Trying generic selectors...")
                    # Try finding articles or list items
                    articles = self.driver.find_elements(By.TAG_NAME, "article")
                    list_items = self.driver.find_elements(By.CSS_SELECTOR, "li.scaffold-finite-scroll__list-item")
                    if self.debug:
                        print(f"  Found {len(articles)} articles, {len(list_items)} list items")
                    if articles:
                        post_elements = articles
                    elif list_items:
                        post_elements = list_items
            
            if not post_elements:
                if self.debug:
                    print("⚠ No posts found. The profile might have no posts, or LinkedIn's structure has changed.")
                    # Debug: Save page source for inspection
                    try:
                        debug_file = "linkedin_debug.html"
                        with open(debug_file, "w", encoding="utf-8") as f:
                            f.write(self.driver.page_source)
                        print(f"  Saved page HTML to {debug_file} for inspection")
                    except:
                        pass
                return []
            
            # Extract post data
            scroll_pause_time = 2
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            processed_texts = set()  # Track processed posts to avoid duplicates
            
            while len(posts) < max_posts:
                # Re-find posts after scrolling
                current_elements = []
                for selector in post_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and len(elements) > 0:
                            current_elements = elements
                            break
                    except:
                        continue
                
                if not current_elements:
                    # Try generic selectors
                    current_elements = self.driver.find_elements(By.TAG_NAME, "article")
                    if not current_elements:
                        current_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.scaffold-finite-scroll__list-item")
                
                for element in current_elements:
                    if len(posts) >= max_posts:
                        break
                    
                    try:
                        # Extract text content - try multiple strategies
                        text_content = ""
                        text_selectors = [
                            "span.feed-shared-text-view__text",
                            "span.break-words",
                            "div.feed-shared-text-view__text-view",
                            "div.update-components-text",
                            "div.feed-shared-update-v2__description-wrapper",
                        ]
                        
                        for text_selector in text_selectors:
                            try:
                                text_elem = element.find_element(By.CSS_SELECTOR, text_selector)
                                text_content = text_elem.text.strip()
                                if text_content and len(text_content) > 10:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        # If no specific text element found, try getting all text from element
                        if not text_content or len(text_content) < 10:
                            text_content = element.text.strip()
                            # Clean up - sometimes we get too much text
                            lines = text_content.split('\n')
                            # Take first few meaningful lines
                            text_content = '\n'.join([line for line in lines[:5] if line.strip()])
                        
                        if not text_content or len(text_content) < 10:
                            continue
                        
                        # Check for duplicates using text hash
                        text_hash = hash(text_content[:100])  # Use first 100 chars as hash
                        if text_hash in processed_texts:
                            continue
                        processed_texts.add(text_hash)
                        
                        # Extract timestamp
                        timestamp = None
                        timestamp_selectors = [
                            "time",
                            "span.feed-shared-actor__sub-description",
                            "span.feed-shared-actor__description",
                            "time[datetime]"
                        ]
                        
                        for ts_selector in timestamp_selectors:
                            try:
                                time_elem = element.find_element(By.CSS_SELECTOR, ts_selector)
                                timestamp = time_elem.get_attribute("datetime") or time_elem.text
                                if timestamp:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        # Extract engagement metrics
                        metrics = {
                            'likes': 0,
                            'comments': 0,
                            'shares': 0
                        }
                        
                        # Create post dict
                        post_data = {
                            'text': text_content,
                            'timestamp': timestamp,
                            'url': activity_url,
                            'metrics': metrics
                        }
                        
                        posts.append(post_data)
                        if self.debug:
                            print(f"  ✓ Extracted post {len(posts)}: {text_content[:60]}...")
                    
                    except Exception as e:
                        if self.debug:
                            print(f"  ⚠ Error extracting post: {e}")
                        continue
                
                # Scroll down to load more posts
                if len(posts) < max_posts:
                    # Scroll smoothly
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause_time)
                    
                    # Check if we've reached the end
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        if self.debug:
                            print(f"  Reached end of page (found {len(posts)} posts)")
                        break
                    last_height = new_height
            
            if self.debug:
                print(f"✓ Successfully extracted {len(posts)} posts")
            
            return posts[:max_posts]
            
        except TimeoutException as e:
            if self.debug:
                print(f"✗ Timeout error: {e}")
            return posts
        except Exception as e:
            if self.debug:
                print(f"✗ Error scraping posts: {e}")
                import traceback
                traceback.print_exc()
            return posts
    
    def get_user_info(self, profile_url: str) -> Optional[Dict]:
        """
        Get basic user information from LinkedIn profile
        
        Args:
            profile_url: Full LinkedIn profile URL
            
        Returns:
            Dictionary with user information or None
        """
        try:
            if self.debug:
                print(f"Fetching user info from: {profile_url}")
            
            self.driver.get(profile_url)
            time.sleep(3)
            
            user_info = {
                'name': None,
                'headline': None,
                'location': None,
                'url': profile_url
            }
            
            # Extract name
            try:
                name_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.text-heading-xlarge, h1.pv-text-details__left-panel h1"))
                )
                user_info['name'] = name_elem.text.strip()
            except:
                pass
            
            # Extract headline
            try:
                headline_elem = self.driver.find_element(By.CSS_SELECTOR, "div.text-body-medium.break-words, div.pv-text-details__left-panel div")
                user_info['headline'] = headline_elem.text.strip()
            except:
                pass
            
            # Extract location
            try:
                location_elem = self.driver.find_element(By.CSS_SELECTOR, "span.text-body-small.inline.t-black--light.break-words")
                user_info['location'] = location_elem.text.strip()
            except:
                pass
            
            if user_info['name']:
                return user_info
            return None
            
        except Exception as e:
            if self.debug:
                print(f"Error fetching user info: {e}")
            return None
    
    def save_posts_to_file(self, posts: List[Dict], output_file: str, profile_url: str = ""):
        """
        Save extracted posts to a text file
        
        Args:
            posts: List of post dictionaries
            output_file: Path to output file
            profile_url: LinkedIn profile URL (optional, for header)
        """
        if not posts:
            if self.debug:
                print("  ⚠ No posts to save")
            return
        
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                if profile_url:
                    f.write(f"LinkedIn Posts from: {profile_url}\n")
                f.write(f"Extracted: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total posts: {len(posts)}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write each post
                for i, post in enumerate(posts, 1):
                    f.write(f"Post {i}\n")
                    f.write("-" * 80 + "\n")
                    if post.get('timestamp'):
                        f.write(f"Timestamp: {post['timestamp']}\n")
                    f.write(f"Text:\n{post['text']}\n")
                    f.write("\n" + "=" * 80 + "\n\n")
            
            if self.debug:
                print(f"  ✓ Saved {len(posts)} posts to: {output_file}")
                
        except Exception as e:
            print(f"  ✗ Error saving to file: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            if self.debug:
                print("✓ Browser closed")


if __name__ == "__main__":
    # Test the scraper
    print("\n" + "=" * 50)
    print("LinkedIn Scraper Test")
    print("=" * 50)
    
    scraper = LinkedInScraper(headless=False, debug=True)
    
    try:
        # Step 1: Login
        print("\nStep 1: Logging in to LinkedIn...")
        login_success = scraper.login()
        
        if not login_success:
            print("\n❌ Login failed. Please check your credentials.")
            print("\nMake sure you have set in your .env file:")
            print("  LINKEDIN_EMAIL=your_email@example.com")
            print("  LINKEDIN_PASSWORD=your_password")
            scraper.close()
            exit(1)
        
        # Step 2: Get user info (test with a profile)
        print("\nStep 2: Testing user info extraction...")
        # Replace with a real LinkedIn profile URL
        test_profile = input("\nEnter a LinkedIn profile URL to test (or press Enter to skip): ").strip()
        
        if test_profile:
            user_info = scraper.get_user_info(test_profile)
            if user_info:
                print(f"\n✓ User info extracted:")
                print(f"  Name: {user_info.get('name', 'N/A')}")
                print(f"  Headline: {user_info.get('headline', 'N/A')}")
                print(f"  Location: {user_info.get('location', 'N/A')}")
        
        # Step 3: Get user posts
        if test_profile:
            print(f"\nStep 3: Testing post extraction from profile...")
            posts = scraper.get_user_posts(test_profile, max_posts=10)
            
            if posts:
                print(f"\n✓ SUCCESS! Found {len(posts)} post(s):\n")
                for i, post in enumerate(posts, 1):
                    print(f"Post {i}:")
                    print(f"  Text: {post['text'][:200]}..." if len(post['text']) > 200 else f"  Text: {post['text']}")
                    print(f"  Timestamp: {post.get('timestamp', 'N/A')}")
                    print()
                
                # Step 4: Save posts to text file
                print("\nStep 4: Saving posts to file...")
                # Extract username from profile URL
                username = test_profile.rstrip('/').split('/')[-1]
                output_file = f"data/linkedin_posts_{username}.txt"
                scraper.save_posts_to_file(posts, output_file, test_profile)
            else:
                print("\n⚠ No posts found. This could mean:")
                print("  - The profile has no posts")
                print("  - Posts are private")
                print("  - LinkedIn's structure has changed")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        scraper.close()

