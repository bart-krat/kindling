import os
from typing import Optional, List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path='.env')


class PromptSummarizer:
    def __init__(self, debug: bool = False, model: str = "gpt-4o-mini"):
        """
        Initialize prompt summarizer for converting character summaries to image generation prompts
        
        Args:
            debug: Print debug information
            model: OpenAI model to use (default: "gpt-4o-mini")
        """
        self.debug = debug
        self.model = model
        self.client = None
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY required in .env file")
        
        self.client = OpenAI(api_key=api_key)
        
        if debug:
            print("✓ PromptSummarizer initialized with OpenAI API")
    
    def create_image_prompt(self, character_summary: str, person_name: Optional[str] = None) -> Optional[str]:
        """
        Convert a character summary into a two-sentence prompt for image generation
        
        Args:
            character_summary: Text summary describing the person's personality, interests, lifestyle, etc.
            person_name: Optional name of the person (if provided, will be used in the prompt)
            
        Returns:
            Two-sentence prompt string for image generation, or None on error
        """
        if not character_summary or not character_summary.strip():
            if self.debug:
                print("  ✗ Empty character summary provided")
            return None
        
        # Build the prompt for OpenAI
        system_prompt = """You are a prompt engineer for image generation. Your task is to convert character summaries into concise, vivid two-sentence prompts that describe how to visualize a person in an image.

The prompt should:
1. Start with "Make an image of [person]..." or "Create an image of [person]..."
2. Describe the person's appearance, personality, and key characteristics
3. Include their interests, lifestyle, or activities
4. Be specific and visual, suitable for image generation models
5. Be exactly two sentences
6. Focus on visual elements that can be represented in an image

Example format:
"Make an image of a person who is an innovative tech entrepreneur, adventurous traveler, and cultural enthusiast. The person should appear social and outgoing, surrounded by elements that represent innovation and collaboration, with a modern and dynamic aesthetic."
"""
        
        user_prompt = f"""Convert the following character summary into a two-sentence image generation prompt:

Character Summary:
{character_summary.strip()}

{f"Person's name: {person_name}" if person_name else ""}

Generate a two-sentence prompt that starts with "Make an image of {person_name if person_name else 'this person'}" and describes how to visualize them based on the summary."""
        
        try:
            if self.debug:
                print(f"  Creating image prompt from character summary...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            prompt = response.choices[0].message.content.strip()
            
            if self.debug:
                print(f"  ✓ Generated prompt: {prompt[:100]}...")
            
            return prompt
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error creating image prompt: {e}")
            return None
    
    def create_multiple_image_prompts(
        self, 
        character_summary: str, 
        person_name: Optional[str] = None,
        num_prompts: int = 3
    ) -> Optional[List[str]]:
        """
        Generate multiple different image prompts from a character summary for variety
        
        Args:
            character_summary: Text summary describing the person's personality, interests, lifestyle, etc.
            person_name: Optional name of the person (if provided, will be used in the prompt)
            num_prompts: Number of different prompts to generate (default: 3)
            
        Returns:
            List of different prompt strings, or None on error
        """
        if not character_summary or not character_summary.strip():
            if self.debug:
                print("  ✗ Empty character summary provided")
            return None
        
        # Build the prompt for OpenAI to generate multiple variations
        system_prompt = """You are a prompt engineer for image generation. Your task is to convert character summaries into multiple distinct, vivid two-sentence prompts that describe different ways to visualize a person in images.

Each prompt should:
1. Start with "Make an image of [person]..." or "Create an image of [person]..."
2. Describe the person's appearance, personality, and key characteristics
3. Include their interests, lifestyle, or activities
4. Be specific and visual, suitable for image generation models
5. Be exactly two sentences
6. Focus on visual elements that can be represented in an image
7. Each prompt should emphasize DIFFERENT aspects or contexts to create variety

Generate multiple prompts that explore different facets, settings, or moods while staying true to the character summary."""
        
        user_prompt = f"""Convert the following character summary into {num_prompts} DIFFERENT two-sentence image generation prompts. Each prompt should explore a different aspect, setting, mood, or context while staying true to the character.

Character Summary:
{character_summary.strip()}

{f"Person's name: {person_name}" if person_name else ""}

Generate {num_prompts} distinct prompts, each starting with "Make an image of {person_name if person_name else 'this person'}" but focusing on different visual interpretations, contexts, or aspects of their personality. Number each prompt (1, 2, 3, etc.)."""
        
        try:
            if self.debug:
                print(f"  Creating {num_prompts} different image prompts from character summary...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.9,  # Higher temperature for more variety
                max_tokens=600  # More tokens for multiple prompts
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse the response to extract individual prompts
            # The prompts might be numbered or separated by newlines
            prompts = []
            
            # Try to split by numbered items (1., 2., 3., etc.)
            import re
            # Split by numbered patterns or double newlines
            parts = re.split(r'\n\s*\d+[\.\)]\s*', content)
            if len(parts) > 1:
                # Remove the first part if it's just intro text
                parts = [p.strip() for p in parts[1:] if p.strip()]
            else:
                # Try splitting by double newlines
                parts = re.split(r'\n\n+', content)
                parts = [p.strip() for p in parts if p.strip()]
            
            # Clean up each prompt
            for part in parts:
                # Remove numbering if present
                cleaned = re.sub(r'^\d+[\.\)]\s*', '', part.strip())
                # Remove quotes if present
                cleaned = cleaned.strip('"\'')
                if cleaned and len(cleaned) > 20:  # Ensure it's a substantial prompt
                    prompts.append(cleaned)
            
            # If we didn't get enough prompts, try to split by sentences
            if len(prompts) < num_prompts:
                # Fallback: split the content into chunks
                sentences = re.split(r'(?<=[.!?])\s+', content)
                # Group sentences into pairs (two sentences per prompt)
                for i in range(0, len(sentences), 2):
                    if i + 1 < len(sentences):
                        prompt = f"{sentences[i]} {sentences[i+1]}".strip()
                        if prompt and len(prompt) > 20:
                            prompts.append(prompt)
            
            # Limit to requested number
            prompts = prompts[:num_prompts]
            
            # If we still don't have enough, use the original method multiple times
            if len(prompts) < num_prompts:
                if self.debug:
                    print(f"  Warning: Only got {len(prompts)} prompts, generating additional ones...")
                # Generate remaining prompts individually with slight variations
                for i in range(len(prompts), num_prompts):
                    variation_prompt = self.create_image_prompt(
                        character_summary,
                        person_name
                    )
                    if variation_prompt and variation_prompt not in prompts:
                        prompts.append(variation_prompt)
            
            if self.debug:
                print(f"  ✓ Generated {len(prompts)} different prompts")
                for i, prompt in enumerate(prompts, 1):
                    print(f"    Prompt {i}: {prompt[:80]}...")
            
            return prompts if prompts else None
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error creating multiple image prompts: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def text_prompt(self, character_summary: str, person_name: Optional[str] = None) -> Optional[str]:
        """
        Convert a character summary into a single-sentence persona prompt for LLM
        
        Args:
            character_summary: Text summary describing the person's personality, interests, lifestyle, etc.
            person_name: Optional name of the person (if provided, will be used in the prompt)
            
        Returns:
            Single-sentence persona prompt string, or None on error
        """
        if not character_summary or not character_summary.strip():
            if self.debug:
                print("  ✗ Empty character summary provided")
            return None
        
        # Build the prompt for OpenAI
        system_prompt = """You are a prompt engineer for LLM persona creation. Your task is to convert character summaries into a concise, single-sentence persona prompt that describes who the person is.

The prompt should:
1. Start with "You're" or "You are"
2. Be exactly ONE sentence
3. Capture the person's key characteristics, profession, interests, or personality traits
4. Be natural and conversational
5. Be suitable for giving an LLM a persona to adopt

Example format:
"You're a creative entrepreneur who loves hardware and building innovative technology products."
"""
        
        user_prompt = f"""Convert the following character summary into a single-sentence persona prompt:

Character Summary:
{character_summary.strip()}

{f"Person's name: {person_name}" if person_name else ""}

Generate a single sentence that starts with "You're" or "You are" and describes this person's persona based on the summary. It must be exactly one sentence."""
        
        try:
            if self.debug:
                print(f"  Creating text persona prompt from character summary...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            prompt = response.choices[0].message.content.strip()
            
            # Ensure it's a single sentence - remove any extra sentences
            # Split by sentence-ending punctuation
            import re
            sentences = re.split(r'[.!?]+', prompt)
            if sentences:
                # Take the first sentence and add proper ending if needed
                prompt = sentences[0].strip()
                if prompt and not prompt[-1] in '.!?':
                    prompt += '.'
            
            if self.debug:
                print(f"  ✓ Generated text prompt: {prompt}")
            
            return prompt
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error creating text prompt: {e}")
            return None


if __name__ == "__main__":
    # Example usage
    summarizer = PromptSummarizer(debug=True)
    
    example_summary = """Innovative tech entrepreneur, adventurous traveler, cultural enthusiast, 
    social and outgoing, values innovation and collaboration"""
    
    # Test image prompt
    prompt = summarizer.create_image_prompt(example_summary, person_name="Carl Pei")
    
    if prompt:
        print("\n" + "=" * 60)
        print("Generated Image Prompt:")
        print("=" * 60)
        print(prompt)
        print("=" * 60)
    
    # Test text prompt
    text_prompt = summarizer.text_prompt(example_summary, person_name="Carl Pei")
    
    if text_prompt:
        print("\n" + "=" * 60)
        print("Generated Text Persona Prompt:")
        print("=" * 60)
        print(text_prompt)
        print("=" * 60)

