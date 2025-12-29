import os
import base64
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path
import urllib.parse

# Load environment variables
load_dotenv(dotenv_path='.env')


class ImageSearcher:
    def __init__(self, debug: bool = False):
        """
        Initialize image searcher using DataForSEO Google Images API
        
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
        
        # Google Images API endpoint
        self.images_api_url = "https://api.dataforseo.com/v3/serp/google/images/live/advanced"
        
        # Create basic auth header
        credentials = f"{self.login}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        if debug:
            print("✓ ImageSearcher initialized with DataForSEO Google Images API")
    
    def search_images(self, query: str, location_code: int = 2826, language_code: str = "en", max_images: int = 1) -> Optional[Dict]:
        """
        Search Google Images using DataForSEO SERP API, download and save the first image
        
        Args:
            query: Search query
            location_code: Location code (2826 = United States)
            language_code: Language code (en = English)
            max_images: Maximum number of images to return (default: 1)
            
        Returns:
            Dictionary with 'filename' (local path) and 'url' (original URL), or None if no image found
        """
        try:
            if self.debug:
                print(f"Searching Google Images for: {query}")
            
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
                self.images_api_url,
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
                                print(f"  ✓ Found {result['items_count']} image results")
                
                # Extract images from response
                images = self.extract_images_from_response(data, max_images=10)  # Get more to filter out bad URLs
                
                if not images or len(images) == 0:
                    if self.debug:
                        print(f"  ⚠ No images found")
                    return None
                
                # Try each image until we find one that works
                for image_data in images:
                    image_url = image_data.get('url')
                    
                    if not image_url:
                        continue
                    
                    # Skip page URLs (not direct image URLs)
                    if self._is_page_url(image_url):
                        if self.debug:
                            print(f"  ⚠ Skipping page URL: {image_url[:80]}...")
                        continue
                    
                    # Try to download and save the image
                    saved_path = self.download_and_save_image(image_url, query)
                    
                    if saved_path:
                        return {
                            'filename': saved_path,
                            'url': image_url,
                            'title': image_data.get('title'),
                            'source': image_data.get('source')
                        }
                    else:
                        if self.debug:
                            print(f"  ⚠ Failed to download image, trying next...")
                        continue
                
                # If we get here, none of the images worked
                if self.debug:
                    print(f"  ⚠ Could not download any images from the results")
                return None
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
    
    def _is_page_url(self, url: str) -> bool:
        """
        Check if a URL is a page URL (not a direct image URL)
        
        Args:
            url: URL to check
            
        Returns:
            True if it appears to be a page URL, False if it's likely a direct image URL
        """
        if not url:
            return True
        
        url_lower = url.lower()
        
        # Common page URL patterns
        page_indicators = [
            '/wiki/',
            '/article/',
            '/page/',
            '/profile/',
            '?',  # Query parameters often indicate pages
            '#',  # Fragments often indicate pages
        ]
        
        # Direct image URL patterns
        image_indicators = [
            '.jpg',
            '.jpeg',
            '.png',
            '.gif',
            '.webp',
            '/image/',
            '/img/',
            '/photo/',
            '/picture/',
            'i.imgur.com',
            'cdn.',
            'static.',
        ]
        
        # Check for page indicators
        for indicator in page_indicators:
            if indicator in url_lower:
                # But allow if it also has image indicators
                has_image_indicator = any(ind in url_lower for ind in image_indicators)
                if not has_image_indicator:
                    return True
        
        # If it has image indicators, it's likely an image
        if any(ind in url_lower for ind in image_indicators):
            return False
        
        # If URL ends with image extension, it's an image
        if url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return False
        
        # Default: if it's a common domain that serves images, assume it's an image URL
        # Otherwise, be cautious and treat it as a page
        return False  # Let's try to download it anyway
    
    def download_and_save_image(self, image_url: str, query: str) -> Optional[str]:
        """
        Download an image from URL and save it to frontend/public directory
        
        Args:
            image_url: URL of the image to download
            query: Search query (used for filename)
            
        Returns:
            Filename relative to public directory (e.g., 'profile_image_carl_pei.jpg') or None
        """
        try:
            if self.debug:
                print(f"  Downloading image from: {image_url[:80]}...")
            
            # Download the image with headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'
            }
            
            img_response = requests.get(image_url, headers=headers, timeout=30, stream=True)
            img_response.raise_for_status()
            
            # Check if the response is actually an image
            content_type = img_response.headers.get('Content-Type', '').lower()
            if not content_type.startswith('image/'):
                if self.debug:
                    print(f"  ⚠ Response is not an image (Content-Type: {content_type})")
                return None
            
            # Determine file extension from URL or Content-Type
            content_type = img_response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # Try to get extension from URL
                parsed_url = urllib.parse.urlparse(image_url)
                path = parsed_url.path.lower()
                if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    ext = path[path.rfind('.'):]
                else:
                    ext = '.jpg'  # Default to jpg
            
            # Create safe filename from query
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_query = safe_query.replace(' ', '_').lower()[:30]
            filename = f"profile_image_{safe_query}{ext}"
            
            # Get the frontend/public directory path
            # Assuming backend/api/image.py -> backend -> kindling -> frontend/public
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent
            project_dir = backend_dir.parent
            frontend_public_dir = project_dir / "frontend" / "public"
            
            # Create directory if it doesn't exist
            frontend_public_dir.mkdir(parents=True, exist_ok=True)
            
            # Full path to save the image
            full_path = frontend_public_dir / filename
            
            # Save the image
            with open(full_path, 'wb') as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if self.debug:
                print(f"  ✓ Image saved to: {filename}")
            
            # Return just the filename (relative to public directory)
            return filename
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error downloading/saving image: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def extract_images_from_response(self, api_response: Dict, max_images: int = 2) -> List[Dict]:
        """
        Extract image URLs and metadata from DataForSEO API response
        
        Args:
            api_response: API response dictionary
            max_images: Maximum number of images to return
            
        Returns:
            List of image dictionaries
        """
        images = []
        
        try:
            if 'tasks' not in api_response:
                return images
            
            for task in api_response['tasks']:
                if 'result' not in task:
                    continue
                
                for result_item in task['result']:
                    if 'items' not in result_item:
                        continue
                    
                    for item in result_item['items']:
                        if len(images) >= max_images:
                            break
                        
                        # Extract image data
                        image_data = {}
                        
                        # Image URL (primary field) - prefer actual image URLs over page URLs
                        # The API returns 'url' as page URL and 'source_url' as the actual image URL
                        # Priority: source_url > thumbnail > image_url > original > url
                        if 'source_url' in item:
                            # source_url is usually the actual image URL
                            potential_image_url = item['source_url']
                            # Check if it looks like an image URL
                            if self._looks_like_image_url(potential_image_url):
                                image_data['url'] = potential_image_url
                            else:
                                # If source_url doesn't look like an image, try other fields
                                if 'thumbnail' in item:
                                    image_data['url'] = item['thumbnail']
                                elif 'image_url' in item:
                                    image_data['url'] = item['image_url']
                                elif 'original' in item:
                                    image_data['url'] = item['original']
                                else:
                                    image_data['url'] = potential_image_url  # Use source_url anyway as fallback
                        elif 'thumbnail' in item:
                            image_data['url'] = item['thumbnail']
                        elif 'image_url' in item:
                            image_data['url'] = item['image_url']
                        elif 'original' in item:
                            image_data['url'] = item['original']
                        elif 'url' in item:
                            # 'url' is usually a page URL, not an image URL - use as last resort
                            image_data['url'] = item['url']
                        
                        # Title
                        if 'title' in item:
                            image_data['title'] = item['title']
                        
                        # Source/domain
                        if 'source' in item:
                            image_data['source'] = item['source']
                        elif 'domain' in item:
                            image_data['source'] = item['domain']
                        
                        # Source URL
                        if 'source_url' in item:
                            image_data['source_url'] = item['source_url']
                        elif 'link' in item:
                            image_data['source_url'] = item['link']
                        
                        # Dimensions
                        if 'width' in item:
                            image_data['width'] = item['width']
                        if 'height' in item:
                            image_data['height'] = item['height']
                        
                        # Thumbnail
                        if 'thumbnail' in item:
                            image_data['thumbnail'] = item['thumbnail']
                        
                        # Only add if we have a URL
                        if image_data.get('url'):
                            images.append(image_data)
                            
                            if self.debug:
                                print(f"    Image {len(images)}: {image_data.get('url', 'N/A')[:80]}...")
                                if image_data.get('title'):
                                    print(f"      Title: {image_data.get('title', 'N/A')[:60]}...")
            
            if self.debug:
                print(f"  ✓ Extracted {len(images)} images")
            
            return images[:max_images]
            
        except Exception as e:
            if self.debug:
                print(f"  ⚠ Error extracting images: {e}")
                import traceback
                traceback.print_exc()
            return []
    
    def _looks_like_image_url(self, url: str) -> bool:
        """
        Check if a URL looks like a direct image URL
        
        Args:
            url: URL to check
            
        Returns:
            True if it looks like an image URL
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Check for image file extensions
        if url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')):
            return True
        
        # Check for image-related paths
        image_paths = ['/image/', '/img/', '/photo/', '/picture/', '/media/', '/upload/', '/static/', '/assets/', '/commons/']
        if any(path in url_lower for path in image_paths):
            return True
        
        # Check for image CDN domains
        image_domains = ['i.imgur.com', 'cdn.', 'static.', 'images.', 'img.', 'media.', 'upload.']
        if any(domain in url_lower for domain in image_domains):
            return True
        
        return False
    
    def save_images_info(self, images: List[Dict], output_file: str, query: str = ""):
        """
        Save image search results to a JSON file
        
        Args:
            images: List of image dictionaries
            output_file: Path to output file
            query: Search query (for header)
        """
        import json
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            output_data = {
                'query': query,
                'total_images': len(images),
                'images': images
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            if self.debug:
                print(f"\n✓ Image search results saved to: {output_file}")
                
        except Exception as e:
            print(f"✗ Error saving image results: {e}")


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("Google Images Search (DataForSEO API)")
    print("=" * 60)
    
    searcher = ImageSearcher(debug=True)
    
    # Get query from command line or prompt
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("\nEnter a search query: ").strip()
    
    if not query:
        print("❌ No query provided")
        sys.exit(1)
    
    # Search for images
    print(f"\nSearching for images: '{query}'")
    images = searcher.search_images(query, max_images=2)
    
    if images:
        # Display results
        print("\n" + "=" * 60)
        print("IMAGE SEARCH RESULTS")
        print("=" * 60)
        
        for i, image in enumerate(images, 1):
            print(f"\nImage {i}:")
            print(f"  URL: {image.get('url', 'N/A')}")
            if image.get('title'):
                print(f"  Title: {image.get('title', 'N/A')}")
            if image.get('source'):
                print(f"  Source: {image.get('source', 'N/A')}")
            if image.get('source_url'):
                print(f"  Source URL: {image.get('source_url', 'N/A')}")
            if image.get('width') and image.get('height'):
                print(f"  Dimensions: {image.get('width')}x{image.get('height')}")
        
        # Save results
        print("\n" + "=" * 60)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(backend_dir, "data")
        safe_query = query.replace(' ', '_').lower()[:50]
        output_file = os.path.join(data_dir, f"google_images_{safe_query}.json")
        searcher.save_images_info(images, output_file, query)
        
        print("\n✓ Image search complete!")
    else:
        print("\n⚠ No images found")

