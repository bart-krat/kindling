import os
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Load environment variables
load_dotenv(dotenv_path='.env')


class InstagramScraper:
    def __init__(self, headless=False, debug=False):
        """
        Initialize Instagram scraper with Selenium
        
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
            self.wait = WebDriverWait(self.driver, 20)  # Increased timeout for Instagram
            
            if debug:
                print("✓ Selenium WebDriver initialized successfully")
        except WebDriverException as e:
            raise RuntimeError(
                f"Failed to initialize Chrome WebDriver. Make sure ChromeDriver is installed.\n"
                f"Install with: brew install chromedriver (macOS) or download from https://chromedriver.chromium.org/\n"
                f"Error: {e}"
            )
    
    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Login to Instagram
        
        Args:
            username: Instagram username (or use INSTAGRAM_USERNAME from .env)
            password: Instagram password (or use INSTAGRAM_PASSWORD from .env)
            
        Returns:
            True if login successful, False otherwise
        """
        # Get credentials from parameters or environment
        username = username or os.getenv('INSTAGRAM_USERNAME')
        password = password or os.getenv('INSTAGRAM_PASSWORD')
        
        if not username or not password:
            raise ValueError(
                "Instagram credentials required. Provide username/password as parameters "
                "or set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file"
            )
        
        try:
            if self.debug:
                print("Navigating to Instagram login page...")
            
            self.driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(4)
            
            # Handle "Not Now" for save login info prompt if it appears (before login)
            try:
                not_now_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                not_now_button.click()
                time.sleep(1)
            except NoSuchElementException:
                pass
            
            # Enter username - wait longer for element
            if self.debug:
                print("Entering username...")
            username_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            time.sleep(1)  # Small delay after element appears
            username_input.clear()
            username_input.send_keys(username)
            
            # Enter password - wait for element
            if self.debug:
                print("Entering password...")
            password_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            time.sleep(1)
            password_input.clear()
            password_input.send_keys(password)
            
            # Click login button - wait for it to be clickable
            if self.debug:
                print("Clicking login button...")
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            
            # Wait for login to complete - give it time to redirect
            if self.debug:
                print("Waiting for login to complete...")
            time.sleep(5)  # Wait for redirect
            
            # Check current URL
            current_url = self.driver.current_url
            if self.debug:
                print(f"  Current URL after login: {current_url}")
            
            # Handle "Save Your Login Info?" prompt (wait up to 5 seconds)
            try:
                not_now_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]"))
                )
                not_now_button.click()
                time.sleep(1)
            except TimeoutException:
                pass
            
            # Handle "Turn on Notifications" prompt
            try:
                not_now_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]")
                not_now_button.click()
                time.sleep(1)
            except NoSuchElementException:
                pass
            
            # Final check if login was successful
            current_url = self.driver.current_url
            if "login" not in current_url.lower() and "accounts" not in current_url.lower():
                if self.debug:
                    print("✓ Login successful!")
                return True
            else:
                # Check for error messages
                try:
                    error_element = self.driver.find_element(By.ID, "slfErrorAlert")
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
    
    def get_profile_photos(self, profile_url: str, max_photos: int = 20) -> List[Dict]:
        """
        Scrape photos from an Instagram profile
        
        Args:
            profile_url: Instagram profile URL (e.g., https://www.instagram.com/username/)
            max_photos: Maximum number of photos to retrieve
            
        Returns:
            List of photo dictionaries with url, image_url, caption, timestamp, and metrics
        """
        if not self.driver:
            raise RuntimeError("WebDriver not initialized. Call __init__ first.")
        
        photos = []
        
        try:
            # Normalize profile URL
            if not profile_url.startswith('http'):
                profile_url = f"https://www.instagram.com/{profile_url}/"
            elif not profile_url.endswith('/'):
                profile_url = profile_url + '/'
            
            if self.debug:
                print(f"Navigating to profile: {profile_url}")
            
            # Navigate to profile
            self.driver.get(profile_url)
            time.sleep(5)  # Wait for initial page load
            
            # Check if profile exists or is private
            try:
                # Check for "Sorry, this page isn't available" or "This Account is Private"
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "isn't available" in page_text or "This Account is Private" in page_text:
                    if self.debug:
                        print("⚠ Profile is private or doesn't exist")
                    return []
            except:
                pass
            
            # Wait for posts grid to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article, div[role='main']"))
                )
                if self.debug:
                    print("✓ Profile page loaded")
                time.sleep(3)  # Additional wait for posts to render
            except TimeoutException:
                if self.debug:
                    print("⚠ Timeout waiting for profile content, continuing anyway...")
            
            # Find post links - Instagram uses article tags with links
            post_selectors = [
                "article a",  # Most common: links inside article tags
                "div[role='main'] a[href*='/p/']",  # Direct post links in main area
                "a[href*='/p/']",  # Any post link
                "a[href*='/reel/']",  # Reels
            ]
            
            processed_urls = set()  # Track processed posts to avoid duplicates
            scroll_pause_time = 2
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10  # Limit scrolling to avoid infinite loops
            
            while len(photos) < max_photos and scroll_attempts < max_scroll_attempts:
                # Find all post links
                post_links = []
                for selector in post_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            href = elem.get_attribute('href')
                            if href and ('/p/' in href or '/reel/' in href):
                                if href not in processed_urls:
                                    post_links.append((elem, href))
                                    processed_urls.add(href)
                        if post_links:
                            break
                    except Exception as e:
                        if self.debug:
                            print(f"  Selector '{selector}' failed: {e}")
                        continue
                
                # Extract data from found posts
                for element, post_url in post_links[:max_photos - len(photos)]:
                    if len(photos) >= max_photos:
                        break
                    
                    try:
                        photo_data = self._extract_post_data(post_url)
                        if photo_data:
                            photos.append(photo_data)
                            if self.debug:
                                print(f"  ✓ Extracted photo {len(photos)}: {post_url}")
                    except Exception as e:
                        if self.debug:
                            print(f"  ⚠ Error extracting post {post_url}: {e}")
                        continue
                
                # Scroll down to load more posts
                if len(photos) < max_photos:
                    # Scroll smoothly
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause_time)
                    
                    # Check if we've reached the end
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        if self.debug:
                            print(f"  Reached end of page (found {len(photos)} photos)")
                        break
                    last_height = new_height
                    scroll_attempts += 1
            
            if self.debug:
                print(f"✓ Successfully extracted {len(photos)} photos")
            
            return photos[:max_photos]
            
        except TimeoutException as e:
            if self.debug:
                print(f"✗ Timeout error: {e}")
            return photos
        except Exception as e:
            if self.debug:
                print(f"✗ Error scraping photos: {e}")
                import traceback
                traceback.print_exc()
            return photos
    
    def _extract_post_data(self, post_url: str) -> Optional[Dict]:
        """
        Extract data from a single Instagram post
        
        Args:
            post_url: URL of the Instagram post
            
        Returns:
            Dictionary with post data or None
        """
        try:
            # Navigate to post
            self.driver.get(post_url)
            time.sleep(3)
            
            photo_data = {
                'url': post_url,
                'image_url': None,
                'caption': None,
                'timestamp': None,
                'likes': 0,
                'comments': 0,
                'is_video': False
            }
            
            # Extract image URL - try multiple selectors
            image_selectors = [
                "img[style*='object-fit']",
                "article img",
                "div[role='dialog'] img",
                "img[src*='scontent']",
                "img[srcset]",
            ]
            
            for selector in image_selectors:
                try:
                    img_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    image_url = img_elem.get_attribute('src') or img_elem.get_attribute('srcset')
                    if image_url:
                        # Clean up srcset (take first URL)
                        if ',' in image_url:
                            image_url = image_url.split(',')[0].strip().split(' ')[0]
                        photo_data['image_url'] = image_url
                        break
                except NoSuchElementException:
                    continue
            
            # Check if it's a video
            try:
                video_elem = self.driver.find_element(By.CSS_SELECTOR, "video")
                photo_data['is_video'] = True
                # Try to get video thumbnail
                if not photo_data['image_url']:
                    try:
                        video_thumbnail = video_elem.get_attribute('poster')
                        if video_thumbnail:
                            photo_data['image_url'] = video_thumbnail
                    except:
                        pass
            except NoSuchElementException:
                pass
            
            # Extract caption
            caption_selectors = [
                "article span",
                "div[role='dialog'] span",
                "h1 + div span",
            ]
            
            for selector in caption_selectors:
                try:
                    # Get all spans and find the longest one (likely the caption)
                    spans = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for span in spans:
                        text = span.text.strip()
                        if text and len(text) > 20:  # Captions are usually longer
                            photo_data['caption'] = text
                            break
                    if photo_data['caption']:
                        break
                except:
                    continue
            
            # Extract timestamp
            try:
                time_elem = self.driver.find_element(By.CSS_SELECTOR, "time")
                photo_data['timestamp'] = time_elem.get_attribute('datetime') or time_elem.get_attribute('title')
            except NoSuchElementException:
                pass
            
            # Extract likes count
            likes_selectors = [
                "section span",
                "a[href*='/liked_by/'] span",
            ]
            
            for selector in likes_selectors:
                try:
                    likes_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    likes_text = likes_elem.text.strip()
                    # Parse likes (e.g., "1,234 likes" or "1.2K likes")
                    if 'like' in likes_text.lower():
                        likes_str = likes_text.split()[0].replace(',', '').replace('K', '000').replace('M', '000000')
                        try:
                            photo_data['likes'] = int(float(likes_str))
                        except:
                            pass
                        break
                except:
                    continue
            
            # Extract comments count (if available)
            try:
                comments_elem = self.driver.find_element(By.XPATH, "//span[contains(text(), 'comments')]")
                comments_text = comments_elem.text.strip()
                if 'comment' in comments_text.lower():
                    comments_str = comments_text.split()[0].replace(',', '').replace('K', '000').replace('M', '000000')
                    try:
                        photo_data['comments'] = int(float(comments_str))
                    except:
                        pass
            except NoSuchElementException:
                pass
            
            return photo_data
            
        except Exception as e:
            if self.debug:
                print(f"    Error extracting post data: {e}")
            return None
    
    def get_profile_info(self, profile_url: str) -> Optional[Dict]:
        """
        Get basic profile information from Instagram profile
        
        Args:
            profile_url: Instagram profile URL
            
        Returns:
            Dictionary with profile information or None
        """
        try:
            # Normalize profile URL
            if not profile_url.startswith('http'):
                profile_url = f"https://www.instagram.com/{profile_url}/"
            elif not profile_url.endswith('/'):
                profile_url = profile_url + '/'
            
            if self.debug:
                print(f"Fetching profile info from: {profile_url}")
            
            self.driver.get(profile_url)
            time.sleep(3)
            
            profile_info = {
                'username': None,
                'full_name': None,
                'bio': None,
                'followers': None,
                'following': None,
                'posts_count': None,
                'url': profile_url,
                'is_private': False
            }
            
            # Extract username from URL
            username = profile_url.rstrip('/').split('/')[-1]
            profile_info['username'] = username
            
            # Check if private
            try:
                private_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "This Account is Private" in private_text:
                    profile_info['is_private'] = True
                    if self.debug:
                        print("  ⚠ Profile is private")
                    return profile_info
            except:
                pass
            
            # Extract full name
            try:
                name_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1, h2, span[dir='auto']"))
                )
                profile_info['full_name'] = name_elem.text.strip()
            except:
                pass
            
            # Extract bio
            try:
                bio_elem = self.driver.find_element(By.CSS_SELECTOR, "div[dir='auto'] span")
                profile_info['bio'] = bio_elem.text.strip()
            except:
                pass
            
            # Extract stats (followers, following, posts)
            try:
                stats = self.driver.find_elements(By.CSS_SELECTOR, "a span, li span")
                for stat in stats:
                    text = stat.text.strip()
                    # Parse followers
                    if 'followers' in text.lower() or 'follower' in text.lower():
                        followers_str = text.split()[0].replace(',', '').replace('K', '000').replace('M', '000000')
                        try:
                            profile_info['followers'] = int(float(followers_str))
                        except:
                            pass
                    # Parse following
                    elif 'following' in text.lower():
                        following_str = text.split()[0].replace(',', '').replace('K', '000').replace('M', '000000')
                        try:
                            profile_info['following'] = int(float(following_str))
                        except:
                            pass
                    # Parse posts
                    elif 'posts' in text.lower() or 'post' in text.lower():
                        posts_str = text.split()[0].replace(',', '').replace('K', '000').replace('M', '000000')
                        try:
                            profile_info['posts_count'] = int(float(posts_str))
                        except:
                            pass
            except:
                pass
            
            if profile_info['username']:
                return profile_info
            return None
            
        except Exception as e:
            if self.debug:
                print(f"Error fetching profile info: {e}")
            return None
    
    def save_photos_to_file(self, photos: List[Dict], output_file: str, profile_url: str = ""):
        """
        Save extracted photos metadata to a text file
        
        Args:
            photos: List of photo dictionaries
            output_file: Path to output file
            profile_url: Instagram profile URL (optional, for header)
        """
        if not photos:
            if self.debug:
                print("  ⚠ No photos to save")
            return
        
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                if profile_url:
                    f.write(f"Instagram Photos from: {profile_url}\n")
                f.write(f"Extracted: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total photos: {len(photos)}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write each photo
                for i, photo in enumerate(photos, 1):
                    f.write(f"Photo {i}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"URL: {photo.get('url', 'N/A')}\n")
                    if photo.get('image_url'):
                        f.write(f"Image URL: {photo['image_url']}\n")
                    if photo.get('caption'):
                        f.write(f"Caption: {photo['caption']}\n")
                    if photo.get('timestamp'):
                        f.write(f"Timestamp: {photo['timestamp']}\n")
                    f.write(f"Likes: {photo.get('likes', 0)}\n")
                    f.write(f"Comments: {photo.get('comments', 0)}\n")
                    if photo.get('is_video'):
                        f.write(f"Type: Video\n")
                    f.write("\n" + "=" * 80 + "\n\n")
            
            if self.debug:
                print(f"  ✓ Saved {len(photos)} photos metadata to: {output_file}")
                
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
    print("Instagram Scraper Test")
    print("=" * 50)
    
    scraper = InstagramScraper(headless=False, debug=True)
    
    try:
        # Default profile: https://www.instagram.com/getpeid/
        test_profile = "https://www.instagram.com/getpeid/"
        
        # Step 1: Try to access profile directly (without login first)
        print(f"\nStep 1: Accessing profile directly: {test_profile}")
        print("  (Trying without login first - many profiles are public)")
        
        # Try to get profile info first
        profile_info = scraper.get_profile_info(test_profile)
        
        # Check if we got redirected to login page
        current_url = scraper.driver.current_url
        needs_login = "login" in current_url.lower() or "accounts/login" in current_url.lower()
        
        if needs_login:
            print("\n  ⚠ Redirected to login page. Attempting to login...")
            # Step 2: Login if needed
            login_success = scraper.login()
            
            if not login_success:
                print("\n❌ Login failed. Please check your credentials.")
                print("\nMake sure you have set in your .env file:")
                print("  INSTAGRAM_USERNAME=your_username")
                print("  INSTAGRAM_PASSWORD=your_password")
                scraper.close()
                exit(1)
            
            # Try profile info again after login
            profile_info = scraper.get_profile_info(test_profile)
        
        # Step 2/3: Display profile info
        if profile_info:
            print(f"\n✓ Profile info extracted:")
            print(f"  Username: {profile_info.get('username', 'N/A')}")
            print(f"  Full Name: {profile_info.get('full_name', 'N/A')}")
            print(f"  Bio: {profile_info.get('bio', 'N/A')}")
            print(f"  Followers: {profile_info.get('followers', 'N/A')}")
            print(f"  Following: {profile_info.get('following', 'N/A')}")
            print(f"  Posts: {profile_info.get('posts_count', 'N/A')}")
            print(f"  Private: {profile_info.get('is_private', False)}")
        else:
            print("\n⚠ Could not extract profile info")
        
        # Step 3/4: Get profile photos
        print(f"\nStep 2: Testing photo extraction from profile...")
        photos = scraper.get_profile_photos(test_profile, max_photos=20)
        
        if photos:
            print(f"\n✓ SUCCESS! Found {len(photos)} photo(s):\n")
            for i, photo in enumerate(photos, 1):
                print(f"Photo {i}:")
                print(f"  URL: {photo['url']}")
                if photo.get('caption'):
                    caption_preview = photo['caption'][:100] + "..." if len(photo['caption']) > 100 else photo['caption']
                    print(f"  Caption: {caption_preview}")
                print(f"  Likes: {photo.get('likes', 0)}")
                print(f"  Comments: {photo.get('comments', 0)}")
                if photo.get('is_video'):
                    print(f"  Type: Video")
                print()
            
            # Step 4/5: Save photos to text file
            print("\nStep 3: Saving photos metadata to file...")
            # Extract username from profile URL
            username = test_profile.rstrip('/').split('/')[-1].replace('@', '')
            output_file = f"data/instagram_photos_{username}.txt"
            scraper.save_photos_to_file(photos, output_file, test_profile)
        else:
            print("\n⚠ No photos found. This could mean:")
            print("  - The profile has no posts")
            print("  - Posts are private")
            print("  - Instagram's structure has changed")
            print("  - Rate limiting or blocking")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        scraper.close()

