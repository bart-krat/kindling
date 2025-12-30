import os
import sys
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='.env')

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import EmbeddingStore from create_embeddings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from create_embeddings import EmbeddingStore


class PerspectiveGenerator:
    def __init__(self, embedding_model: str = "text-embedding-3-small", 
                 llm_model: str = "gpt-4o-mini", 
                 dimension: int = 1536,
                 debug: bool = False):
        """
        Initialize perspective generator with vector store and LLM
        
        Args:
            embedding_model: Embedding model name (for dimension matching)
            llm_model: LLM model for generating perspectives
            dimension: Dimension of embeddings
            debug: Print debug information
        """
        self.debug = debug
        self.llm_model = llm_model
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY in .env file"
            )
        
        self.client = OpenAI(api_key=api_key)
        self.store = EmbeddingStore(embedding_model=embedding_model, 
                                   dimension=dimension, 
                                   debug=debug)
        
        if debug:
            print(f"✓ PerspectiveGenerator initialized with LLM: {llm_model}")
    
    def load_vector_store(self, index_path: str, metadata_path: str):
        """
        Load the vector store from disk
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata JSON file
        """
        if self.debug:
            print(f"Loading vector store from:")
            print(f"  Index: {index_path}")
            print(f"  Metadata: {metadata_path}")
        
        self.store.load(index_path, metadata_path)
        
        if self.debug:
            print(f"  ✓ Vector store loaded with {self.store.index.ntotal} vectors")
    
    def search_and_generate_perspective(self, query: str, top_k: int = 5, 
                                       max_context_length: int = 2000,
                                       persona_prompt: Optional[str] = None) -> Dict:
        """
        Search vector store and generate a perspective based on retrieved context
        
        Args:
            query: User's question or query
            top_k: Number of relevant documents to retrieve
            max_context_length: Maximum characters of context to include
            persona_prompt: Optional persona prompt to prepend to system message (e.g., "You're a creative entrepreneur...")
            
        Returns:
            Dictionary with 'perspective', 'sources', and 'query'
        """
        if self.debug:
            print(f"\n{'='*60}")
            print(f"Processing query: {query}")
            print(f"{'='*60}")
        
        # Step 1: Search vector store for relevant content
        if self.debug:
            print(f"\nStep 1: Searching vector store...")
        
        results = self.store.search(query, k=top_k)
        
        if not results:
            return {
                'perspective': 'No relevant information found in the knowledge base to answer your question.',
                'sources': [],
                'query': query
            }
        
        if self.debug:
            print(f"  ✓ Found {len(results)} relevant documents")
            for i, result in enumerate(results, 1):
                print(f"\n  Source {i}:")
                print(f"    Category: {result['category']}")
                print(f"    Summary: {result['summary'][:80]}...")
                print(f"    Distance: {result['distance']:.4f}")
        
        # Step 2: Build context from retrieved documents
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            source_text = f"Source {i} (Category: {result['category']}):\n"
            source_text += f"Summary: {result['summary']}\n"
            source_text += f"Content: {result['text']}\n"
            
            if total_length + len(source_text) > max_context_length:
                # Truncate if needed
                remaining = max_context_length - total_length - len("...\n")
                if remaining > 0:
                    source_text = source_text[:remaining] + "...\n"
                    context_parts.append(source_text)
                break
            
            context_parts.append(source_text)
            total_length += len(source_text)
        
        context = "\n".join(context_parts)
        
        # Step 3: Generate perspective using LLM
        if self.debug:
            print(f"\nStep 2: Generating perspective with LLM...")
            print(f"  Context length: {len(context)} characters")
            print(f"  Using model: {self.llm_model}")
        
        prompt = f"""Based on the following context from various sources, provide a thoughtful perspective on the user's question. 

The context includes information from different categories:
- "industry": Technical/industry insights and trends
- "company": Information about companies, products, or services
- "world": General world topics and non-technical views

Your task is to synthesize these perspectives into a coherent, insightful answer that addresses the user's question.

Context:
{context}

User's question: {query}

Instructions:
1. Synthesize the information from the context to form a comprehensive perspective
2. Reference specific insights from the sources where relevant
3. If the context doesn't fully answer the question, acknowledge limitations
4. Provide a clear, well-structured response (2-4 paragraphs)
5. Focus on insights and understanding rather than just summarizing

Provide your perspective:"""
        
        try:
            # Build system message with optional persona prompt
            system_message = "You are a thoughtful analyst who synthesizes information from multiple sources to provide insightful perspectives on questions about the world, industry, and technology."
            
            if persona_prompt:
                # Prepend persona prompt as the first sentence
                system_message = f"{persona_prompt} {system_message}"
                if self.debug:
                    print(f"  Using persona prompt: {persona_prompt}")
            
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            perspective = response.choices[0].message.content.strip()
            
            if self.debug:
                print(f"  ✓ Generated perspective ({len(perspective)} characters)")
            
            # Prepare sources for output
            sources = [
                {
                    'rank': r['rank'],
                    'category': r['category'],
                    'summary': r['summary'],
                    'relevance_score': round(1.0 / (1.0 + r['distance']), 4) if r['distance'] > 0 else 1.0
                }
                for r in results
            ]
            
            return {
                'perspective': perspective,
                'sources': sources,
                'query': query
            }
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error generating perspective: {e}")
                import traceback
                traceback.print_exc()
            
            # Fallback response
            return {
                'perspective': f'I encountered an error while generating a perspective. However, I found {len(results)} relevant sources that might help answer your question: "{query}"',
                'sources': [
                    {
                        'category': r['category'],
                        'summary': r['summary']
                    }
                    for r in results
                ],
                'query': query,
                'error': str(e)
            }
    
    def format_output(self, result: Dict) -> str:
        """
        Format the perspective result for display
        
        Args:
            result: Result dictionary from search_and_generate_perspective
            
        Returns:
            Formatted string
        """
        output = []
        output.append("=" * 70)
        output.append(f"QUERY: {result['query']}")
        output.append("=" * 70)
        output.append("\nPERSPECTIVE:")
        output.append("-" * 70)
        output.append(result['perspective'])
        output.append("\n" + "-" * 70)
        
        if result['sources']:
            output.append(f"\nSOURCES ({len(result['sources'])}):")
            output.append("-" * 70)
            for source in result['sources']:
                output.append(f"\n[{source['rank']}] Category: {source['category']}")
                if 'relevance_score' in source:
                    output.append(f"    Relevance: {source['relevance_score']:.4f}")
                output.append(f"    Summary: {source['summary']}")
        
        output.append("\n" + "=" * 70)
        
        return "\n".join(output)


def find_vector_store_files(data_dir: str) -> tuple:
    """
    Find vector store files in data directory
    
    Args:
        data_dir: Data directory path
        
    Returns:
        Tuple of (index_path, metadata_path) or (None, None) if not found
    """
    index_path = os.path.join(data_dir, "embeddings.index")
    metadata_path = os.path.join(data_dir, "embeddings_metadata.json")
    
    if os.path.exists(index_path) and os.path.exists(metadata_path):
        return index_path, metadata_path
    
    return None, None


if __name__ == "__main__":
    import argparse
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(backend_dir, "data")
    
    parser = argparse.ArgumentParser(
        description="Generate perspectives based on vector store search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python src/perspective.py
  
  # Single query
  python src/perspective.py --query "What are the latest trends in AI?"
  
  # Custom vector store location
  python src/perspective.py --query "Your question" --index data/custom.index --metadata data/custom_metadata.json
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Question or query to process (if not provided, runs in interactive mode)'
    )
    parser.add_argument(
        '--index',
        type=str,
        default=None,
        help='Path to FAISS index file (default: data/embeddings.index)'
    )
    parser.add_argument(
        '--metadata',
        type=str,
        default=None,
        help='Path to metadata JSON file (default: data/embeddings_metadata.json)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of relevant documents to retrieve (default: 5)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o-mini',
        help='LLM model to use (default: gpt-4o-mini)'
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug output'
    )
    
    args = parser.parse_args()
    
    try:
        # Find vector store files
        if args.index and args.metadata:
            index_path = args.index
            metadata_path = args.metadata
        else:
            index_path, metadata_path = find_vector_store_files(data_dir)
            
            if not index_path:
                print(f"\n❌ Vector store not found in {data_dir}")
                print("   Looking for:")
                print(f"     - embeddings.index")
                print(f"     - embeddings_metadata.json")
                print("\n   Run create_embeddings.py first to create the vector store.")
                sys.exit(1)
        
        # Initialize perspective generator
        print("\n" + "=" * 70)
        print("Perspective Generator")
        print("=" * 70)
        
        generator = PerspectiveGenerator(llm_model=args.model, debug=args.debug)
        generator.load_vector_store(index_path, metadata_path)
        
        # Process query
        if args.query:
            # Single query mode
            result = generator.search_and_generate_perspective(args.query, top_k=args.top_k)
            print("\n" + generator.format_output(result))
        else:
            # Interactive mode
            print("\nEntering interactive mode. Type 'quit' or 'exit' to stop.\n")
            
            while True:
                try:
                    query = input("\n🔍 Your question: ").strip()
                    
                    if not query:
                        continue
                    
                    if query.lower() in ['quit', 'exit', 'q']:
                        print("\n👋 Goodbye!")
                        break
                    
                    result = generator.search_and_generate_perspective(query, top_k=args.top_k)
                    print("\n" + generator.format_output(result))
                    
                except KeyboardInterrupt:
                    print("\n\n👋 Goodbye!")
                    break
                except EOFError:
                    print("\n\n👋 Goodbye!")
                    break
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

