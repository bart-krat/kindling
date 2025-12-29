import os
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='.env')

# Try to import OpenAI (user needs to install openai package)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class TextLabeler:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", debug: bool = False):
        """
        Initialize text labeler with LLM
        
        Args:
            api_key: OpenAI API key (or use OPENAI_API_KEY from .env)
            model: Model to use (default: gpt-4o-mini for cost efficiency)
            debug: Print debug information
        """
        self.debug = debug
        self.model = model
        
        # Get API key from parameter or environment
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )
        
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Provide api_key parameter or "
                "set OPENAI_API_KEY in .env file"
            )
        
        self.client = OpenAI(api_key=api_key)
        
        if debug:
            print(f"✓ TextLabeler initialized with model: {model}")
    
    def label_text(self, text: str) -> Dict[str, str]:
        """
        Label a single text with category and summary
        
        Args:
            text: Text to label
            
        Returns:
            Dictionary with 'summary', 'category', and 'text' fields
        """
        prompt = f"""Analyze the following text and provide:
1. A single sentence summary
2. A category: one of "industry", "company", or "world"
   - "industry": Technical/industry insights, trends, or professional content
   - "company": Content about the founder's own company, products, or services
   - "world": Non-technical views, personal opinions, or general world topics

Text to analyze:
{text}

Respond in JSON format with exactly these fields:
{{
    "summary": "single sentence summary here",
    "category": "industry" or "company" or "world"
}}
"""
        
        try:
            if self.debug:
                print(f"  Labeling text: {text[:50]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a text categorization assistant. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure all required fields are present
            labeled = {
                'summary': result.get('summary', ''),
                'category': result.get('category', 'world'),
                'text': text
            }
            
            if self.debug:
                print(f"  ✓ Labeled: {labeled['category']} - {labeled['summary'][:50]}...")
            
            return labeled
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error labeling text: {e}")
            # Return default structure on error
            return {
                'summary': 'Unable to generate summary',
                'category': 'world',
                'text': text
            }
    
    def label_texts(self, texts: List[str], batch_size: int = 10) -> List[Dict[str, str]]:
        """
        Label multiple texts
        
        Args:
            texts: List of texts to label
            batch_size: Process in batches (to avoid rate limits)
            
        Returns:
            List of labeled text dictionaries
        """
        labeled_texts = []
        
        if self.debug:
            print(f"Labeling {len(texts)} texts...")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            if self.debug:
                print(f"  Processing batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
            
            for text in batch:
                labeled = self.label_text(text)
                labeled_texts.append(labeled)
        
        if self.debug:
            print(f"✓ Labeled {len(labeled_texts)} texts")
        
        return labeled_texts
    
    def save_labeled_texts(self, labeled_texts: List[Dict[str, str]], output_file: str, format: str = 'json'):
        """
        Save labeled texts to a file
        
        Args:
            labeled_texts: List of labeled text dictionaries
            output_file: Path to output file
            format: Output format - 'json' (JSON lines) or 'txt' (readable text)
        """
        if not labeled_texts:
            print(f"  ⚠ No labeled texts to save")
            return
        
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
            
            if format == 'json':
                # Save as JSON lines (one JSON object per line)
                with open(output_file, 'w', encoding='utf-8') as f:
                    for labeled in labeled_texts:
                        f.write(json.dumps(labeled, ensure_ascii=False) + '\n')
                
                if self.debug:
                    print(f"  ✓ Saved {len(labeled_texts)} labeled texts to {output_file} (JSON lines)")
            
            elif format == 'txt':
                # Save as readable text format
                with open(output_file, 'w', encoding='utf-8') as f:
                    for i, labeled in enumerate(labeled_texts, 1):
                        f.write(f"=== Entry {i} ===\n")
                        f.write(f"Category: {labeled['category']}\n")
                        f.write(f"Summary: {labeled['summary']}\n")
                        f.write(f"Text: {labeled['text']}\n")
                        f.write("\n")
                
                if self.debug:
                    print(f"  ✓ Saved {len(labeled_texts)} labeled texts to {output_file} (text format)")
            
            else:
                raise ValueError(f"Unknown format: {format}. Use 'json' or 'txt'")
                
        except Exception as e:
            print(f"  ✗ Error saving to file: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Test the labeler with text from test_post.txt
    print("\n" + "=" * 50)
    print("Text Labeler Test")
    print("=" * 50)
    
    # Read text from test_post.txt
    test_file = "data/test_post.txt"
    
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)  # Go up one level from src/ to backend/
        test_file_path = os.path.join(backend_dir, test_file)
        
        if not os.path.exists(test_file_path):
            print(f"❌ File not found: {test_file_path}")
            print(f"   Looking for: {test_file}")
            exit(1)
        
        print(f"\nReading text from: {test_file}")
        with open(test_file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("❌ File is empty")
            exit(1)
        
        print(f"\nText to categorize:")
        print("-" * 50)
        print(text)
        print("-" * 50)
        
        # Initialize labeler
        labeler = TextLabeler(debug=True)
        
        # Label the text
        print("\nLabeling text...")
        labeled = labeler.label_text(text)
        
        # Display results
        print("\n" + "=" * 50)
        print("Results:")
        print("=" * 50)
        print(f"\nCategory: {labeled['category']}")
        print(f"Summary: {labeled['summary']}")
        print(f"\nOriginal Text:")
        print(f"{labeled['text']}")
        
        # Save to file
        print("\n" + "=" * 50)
        output_dir = os.path.join(backend_dir, "data")
        os.makedirs(output_dir, exist_ok=True)
        
        output_json = os.path.join(output_dir, "labeled_test_post.json")
        output_txt = os.path.join(output_dir, "labeled_test_post.txt")
        
        labeler.save_labeled_texts([labeled], output_json, format='json')
        labeler.save_labeled_texts([labeled], output_txt, format='txt')
        
        print(f"\n✓ Results saved to:")
        print(f"  - {output_json}")
        print(f"  - {output_txt}")
        
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        print(f"   Make sure {test_file} exists in the backend directory")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()