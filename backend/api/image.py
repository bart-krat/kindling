import os
import base64
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

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
    
    def search_images(self, query: str, location_code: int = 2826, language_code: str = "en", max_images: int = 2) -> List[Dict]:
        """
        Search Google Images using DataForSEO SERP API
        
        Args:
            query: Search query
            location_code: Location code (2826 = United States)
            language_code: Language code (en = English)
            max_images: Maximum number of images to return (default: 2)
            
        Returns:
            List of image dictionaries with url, title, source, etc.
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
                images = self.extract_images_from_response(data, max_images)
                
                return images
            else:
                if self.debug:
                    print(f"  ✗ API Error: HTTP {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"    Error: {error_data}")
                    except:
                        print(f"    Response: {response.text[:200]}")
                return []
                
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
            return []
    
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
                        
                        # Image URL (primary field)
                        if 'url' in item:
                            image_data['url'] = item['url']
                        elif 'image_url' in item:
                            image_data['url'] = item['image_url']
                        elif 'original' in item:
                            image_data['url'] = item['original']
                        
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

