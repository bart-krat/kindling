import os
import json
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

# Lazy import replicate to avoid compatibility issues with Python 3.14 at startup
# Only import when ImageGenerator is actually instantiated


class ImageGenerator:
    def __init__(self, debug: bool = False):
        """
        Initialize image generator using Replicate API
        
        Args:
            debug: Print debug information
        """
        self.debug = debug
        
        # Get Replicate API token
        self.replicate_token = os.getenv('REPLICATE_API_TOKEN')
        if not self.replicate_token:
            raise ValueError("REPLICATE_API_TOKEN required in .env file")
        
        # Set Replicate API token
        os.environ['REPLICATE_API_TOKEN'] = self.replicate_token
        
        # Lazy import replicate here to avoid compatibility issues at module import time
        try:
            import replicate
            self.replicate = replicate
        except ImportError as e:
            raise ImportError(f"Failed to import replicate: {e}. Please ensure replicate is installed: pip install replicate")
        except Exception as e:
            raise RuntimeError(f"Error initializing replicate: {e}. This may be due to Python 3.14 compatibility issues. Consider using Python 3.13 or earlier.")
        
        if debug:
            print("✓ ImageGenerator initialized with Replicate API")
    
    def generate_image(
        self,
        prompt: str,
        subject_reference: str,
        aspect_ratio: str = "3:4",
        number_of_images: int = 1,
        prompt_optimizer: bool = True
    ) -> Optional[Dict]:
        """
        Generate an image using minimax/image-01 model
        
        Args:
            prompt: Text prompt describing the desired output
            subject_reference: Path or URL to the base/reference image
            aspect_ratio: Aspect ratio for the output (default: "3:4")
            number_of_images: Number of images to generate (default: 1)
            prompt_optimizer: Whether to optimize the prompt (default: True)
            
        Returns:
            Dictionary with generated image URLs and metadata, or None
        """
        try:
            if self.debug:
                print(f"Generating image with minimax/image-01...")
                print(f"  Prompt: {prompt}")
                print(f"  Subject Reference: {subject_reference}")
                print(f"  Aspect Ratio: {aspect_ratio}")
            
            # Handle local file paths - open as file object for Replicate
            if os.path.exists(subject_reference) and not subject_reference.startswith(('http://', 'https://')):
                subject_reference = open(subject_reference, 'rb')
            
            # Run the model
            output = self.replicate.run(
                "minimax/image-01",
                input={
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "number_of_images": number_of_images,
                    "prompt_optimizer": prompt_optimizer,
                    "subject_reference": subject_reference
                }
            )
            
            # Extract image URLs from output
            image_urls = []
            if isinstance(output, list):
                for item in output:
                    if hasattr(item, 'url'):
                        image_urls.append(item.url)
                    elif isinstance(item, str):
                        image_urls.append(item)
            elif hasattr(output, 'url'):
                image_urls.append(output.url)
            elif isinstance(output, str):
                image_urls.append(output)
            
            result = {
                'image_urls': image_urls,
                'prompt': prompt,
                'subject_reference': subject_reference,
                'aspect_ratio': aspect_ratio
            }
            
            if self.debug:
                print(f"  ✓ Generated {len(image_urls)} image(s)")
                for i, url in enumerate(image_urls, 1):
                    print(f"    Image {i}: {url}")
            
            return result
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error generating image: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def save_image(self, image_url: str, output_path: str) -> bool:
        """
        Download and save an image from URL
        
        Args:
            image_url: URL of the image
            output_path: Path to save the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.debug:
                print(f"Downloading image to: {output_path}")
            
            import requests
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            # Create directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
            
            # Save image
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            if self.debug:
                print(f"  ✓ Image saved successfully")
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error downloading image: {e}")
            return False


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("Image Generator (Replicate - minimax/image-01)")
    print("=" * 60)
    
    generator = ImageGenerator(debug=True)
    
    # Default values
    base_image_path = "/Users/bartkratochvil/Desktop/Projects/kindling/backend/data/carl.jpeg"
    prompt = "Image of Carl as an adventurer, trying to create unique technology surrounded by a community"
    
    # Get prompt from command line if provided
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    
    # Generate image
    print(f"\nGenerating image...")
    print(f"Prompt: {prompt}")
    print(f"Base Image: {base_image_path}\n")
    
    result = generator.generate_image(
        prompt=prompt,
        subject_reference=base_image_path,
        aspect_ratio="3:4",
        number_of_images=1,
        prompt_optimizer=True
    )
    
    if result and result.get('image_urls'):
        # Save the generated image
        output_path = "data/generated_avatar.png"
        success = generator.save_image(result['image_urls'][0], output_path)
        
        if success:
            print("\n" + "=" * 60)
            print("GENERATION COMPLETE")
            print("=" * 60)
            print(f"\nGenerated image saved to: {output_path}")
            print(f"Image URL: {result['image_urls'][0]}")
            print("\n✓ Image generation complete!")
        else:
            print("\n⚠ Image generated but failed to save")
    else:
        print("\n❌ Image generation failed")
