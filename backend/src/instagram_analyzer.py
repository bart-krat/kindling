import os
import re
import base64
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import io

load_dotenv(dotenv_path='.env')


class InstagramImageAnalyzer:
    def __init__(self, debug: bool = False):
        """
        Initialize Instagram image analyzer
        
        Args:
            debug: Print debug information
        """
        self.debug = debug
        self.client = None
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY required in .env file")
        
        self.client = OpenAI(api_key=api_key)
        
        # Headers for downloading images
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def parse_instagram_photos_file(self, file_path: str) -> List[Dict]:
        """
        Parse the Instagram photos text file to extract image URLs
        
        Args:
            file_path: Path to instagram_photos_*.txt file
            
        Returns:
            List of dictionaries with photo data
        """
        photos = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by photo separator
        photo_sections = content.split('Photo ')
        
        for section in photo_sections[1:]:  # Skip first empty section
            photo_data = {}
            
            # Extract URL
            url_match = re.search(r'URL: (https://[^\n]+)', section)
            if url_match:
                photo_data['url'] = url_match.group(1)
            
            # Extract Image URL
            image_url_match = re.search(r'Image URL: (https://[^\n]+)', section)
            if image_url_match:
                photo_data['image_url'] = image_url_match.group(1)
            
            # Extract caption
            caption_match = re.search(r'Caption: (.+?)(?=\n[A-Z]|\n===)', section, re.DOTALL)
            if caption_match:
                photo_data['caption'] = caption_match.group(1).strip()
            
            # Extract timestamp
            timestamp_match = re.search(r'Timestamp: ([^\n]+)', section)
            if timestamp_match:
                photo_data['timestamp'] = timestamp_match.group(1)
            
            if photo_data.get('image_url'):
                photos.append(photo_data)
        
        if self.debug:
            print(f"✓ Parsed {len(photos)} photos from file")
        
        return photos
    
    def download_image(self, image_url: str) -> Optional[bytes]:
        """
        Download image from URL
        
        Args:
            image_url: URL of the image
            
        Returns:
            Image bytes or None if failed
        """
        try:
            response = requests.get(image_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Check if it's actually an image
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                if self.debug:
                    print(f"  ⚠ URL doesn't appear to be an image: {content_type}")
                return None
            
            return response.content
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error downloading image: {e}")
            return None
    
    def image_to_base64(self, image_bytes: bytes, max_size: int = 1024) -> Optional[str]:
        """
        Convert image bytes to base64, optionally resizing to reduce size
        
        Args:
            image_bytes: Raw image bytes
            max_size: Maximum width/height in pixels (for cost optimization)
            
        Returns:
            Base64 encoded string with data URI prefix
        """
        try:
            # Open image with PIL
            img = Image.open(io.BytesIO(image_bytes))
            
            # Get format
            img_format = img.format or 'JPEG'
            
            # Resize if too large (to reduce API costs)
            if max_size and (img.width > max_size or img.height > max_size):
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (for JPEG)
            if img_format == 'JPEG' and img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format=img_format, quality=85)
            image_bytes = buffer.getvalue()
            
            # Encode to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Determine MIME type
            mime_type = f"image/{img_format.lower()}" if img_format else "image/jpeg"
            
            # Return data URI format
            return f"data:{mime_type};base64,{base64_image}"
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error converting image to base64: {e}")
            return None
    
    def analyze_image(self, base64_image: str, caption: str = "", prompt: str = None) -> Optional[str]:
        """
        Analyze a single image using GPT-4 Vision
        
        Args:
            base64_image: Base64 encoded image (with data URI prefix)
            caption: Optional caption from Instagram post
            prompt: Custom prompt (default analyzes person's interests/lifestyle)
            
        Returns:
            Analysis text or None
        """
        if not prompt:
            prompt = """Analyze this Instagram photo and describe:
1. What the person is doing or what the photo shows
2. The setting/environment
3. Any visible interests, hobbies, or lifestyle indicators
4. The mood or tone of the photo
5. Any objects, activities, or themes that reveal personality traits

Be concise but insightful. Focus on what this photo reveals about the person's interests, values, or lifestyle."""
        
        if caption:
            prompt += f"\n\nInstagram caption: {caption}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # or "gpt-4-vision-preview" for older models
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": base64_image
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error analyzing image: {e}")
            return None
    
    def analyze_profile_photos(self, photos: List[Dict], max_photos: int = 20) -> Dict:
        """
        Analyze multiple photos and create a profile summary
        
        Args:
            photos: List of photo dictionaries from parse_instagram_photos_file
            max_photos: Maximum number of photos to analyze
            
        Returns:
            Dictionary with individual analyses and summary
        """
        if self.debug:
            print(f"\nAnalyzing {min(len(photos), max_photos)} photos...")
        
        analyses = []
        successful = 0
        
        for i, photo in enumerate(photos[:max_photos], 1):
            if self.debug:
                print(f"\n  Processing photo {i}/{min(len(photos), max_photos)}...")
            
            # Download image
            image_bytes = self.download_image(photo['image_url'])
            if not image_bytes:
                continue
            
            # Convert to base64
            base64_image = self.image_to_base64(image_bytes, max_size=1024)
            if not base64_image:
                continue
            
            # Analyze
            analysis = self.analyze_image(
                base64_image,
                caption=photo.get('caption', '')
            )
            
            if analysis:
                analyses.append({
                    'photo_number': i,
                    'url': photo.get('url', ''),
                    'timestamp': photo.get('timestamp', ''),
                    'caption': photo.get('caption', ''),
                    'analysis': analysis
                })
                successful += 1
                
                if self.debug:
                    print(f"    ✓ Analyzed successfully")
        
        if self.debug:
            print(f"\n✓ Successfully analyzed {successful}/{min(len(photos), max_photos)} photos")
        
        # Create overall summary
        summary = self.create_profile_summary(analyses)
        
        return {
            'individual_analyses': analyses,
            'summary': summary,
            'total_photos_analyzed': successful
        }
    
    def create_profile_summary(self, analyses: List[Dict]) -> str:
        """
        Create an overall profile summary from individual photo analyses
        
        Args:
            analyses: List of individual photo analyses
            
        Returns:
            Summary text
        """
        if not analyses:
            return "No photos were successfully analyzed."
        
        # Combine all analyses into a prompt
        combined_analyses = "\n\n".join([
            f"Photo {a['photo_number']} ({a.get('timestamp', 'unknown date')}):\n"
            f"Caption: {a.get('caption', 'No caption')}\n"
            f"Analysis: {a['analysis']}"
            for a in analyses
        ])
        
        prompt = f"""Based on the following analyses of Instagram photos, create a comprehensive profile summary of this person.

Photo Analyses:
{combined_analyses}

Please provide:
1. Overall personality traits and interests
2. Lifestyle and activities
3. Values and priorities (if evident)
4. Professional or creative pursuits
5. Social patterns or themes
6. Any notable characteristics or patterns across the photos

Be insightful and specific, drawing connections between different photos."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error creating summary: {e}")
            return "Error creating summary."
    
    def save_analysis(self, analysis_result: Dict, output_file: str):
        """
        Save analysis results to a JSON file
        
        Args:
            analysis_result: Result from analyze_profile_photos
            output_file: Path to output JSON file
        """
        import json
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            
            if self.debug:
                print(f"\n✓ Analysis saved to: {output_file}")
                
        except Exception as e:
            print(f"✗ Error saving analysis: {e}")


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("Instagram Image Analyzer")
    print("=" * 60)
    
    # Get file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "data/instagram_photos_getpeid.txt"
    
    if not os.path.exists(input_file):
        print(f"\n❌ File not found: {input_file}")
        print("\nUsage: python instagram_analyzer.py <path_to_instagram_photos_file>")
        sys.exit(1)
    
    analyzer = InstagramImageAnalyzer(debug=True)
    
    try:
        # Step 1: Parse photos file
        print(f"\nStep 1: Parsing photos file: {input_file}")
        photos = analyzer.parse_instagram_photos_file(input_file)
        
        if not photos:
            print("  ⚠ No photos found in file")
            sys.exit(1)
        
        print(f"  ✓ Found {len(photos)} photos")
        
        # Step 2: Analyze photos
        print(f"\nStep 2: Analyzing photos (this may take a few minutes)...")
        result = analyzer.analyze_profile_photos(photos, max_photos=20)
        
        # Step 3: Display results
        print("\n" + "=" * 60)
        print("PROFILE SUMMARY")
        print("=" * 60)
        print(result['summary'])
        
        print(f"\n\nAnalyzed {result['total_photos_analyzed']} photos")
        
        # Step 4: Save results
        output_file = input_file.replace('.txt', '_analysis.json')
        analyzer.save_analysis(result, output_file)
        
        print("\n✓ Analysis complete!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()