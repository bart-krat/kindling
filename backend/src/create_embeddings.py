import os
import json
import faiss
import numpy as np
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


class EmbeddingStore:
    def __init__(self, embedding_model: str = "text-embedding-3-small", dimension: int = 1536, debug: bool = False):
        """
        Initialize embedding store with FAISS
        
        Args:
            embedding_model: OpenAI embedding model to use
            dimension: Dimension of embeddings (1536 for text-embedding-3-small, 3072 for text-embedding-3-large)
            debug: Print debug information
        """
        self.debug = debug
        self.embedding_model = embedding_model
        self.dimension = dimension
        
        # Initialize OpenAI client
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
        
        # Initialize FAISS index (L2 distance)
        self.index = faiss.IndexFlatL2(dimension)
        
        # Store metadata (summary, category, text) for each embedding
        self.metadata = []
        
        if debug:
            print(f"✓ EmbeddingStore initialized with model: {embedding_model}")
            print(f"  Dimension: {dimension}")
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for a list of texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of embeddings
        """
        if not texts:
            return np.array([])
        
        if self.debug:
            print(f"  Creating embeddings for {len(texts)} texts...")
        
        try:
            # Use OpenAI embeddings API
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            # Extract embeddings
            embeddings = np.array([item.embedding for item in response.data])
            
            # Verify dimension matches
            if embeddings.shape[1] != self.dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self.dimension}, "
                    f"got {embeddings.shape[1]}. Update dimension parameter."
                )
            
            if self.debug:
                print(f"  ✓ Created embeddings with shape: {embeddings.shape}")
            
            return embeddings
            
        except Exception as e:
            if self.debug:
                print(f"  ✗ Error creating embeddings: {e}")
            raise
    
    def add_texts(self, texts: List[str], metadata_list: List[Dict]):
        """
        Add texts with metadata to the vector store
        
        Args:
            texts: List of texts to embed and add
            metadata_list: List of metadata dictionaries (one per text)
        """
        if len(texts) != len(metadata_list):
            raise ValueError("Number of texts must match number of metadata entries")
        
        if not texts:
            return
        
        if self.debug:
            print(f"Adding {len(texts)} texts to vector store...")
        
        # Create embeddings
        embeddings = self.create_embeddings(texts)
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Store metadata
        self.metadata.extend(metadata_list)
        
        if self.debug:
            print(f"  ✓ Added {len(texts)} texts. Total vectors: {self.index.ntotal}")
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Search for similar texts
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of dictionaries with 'text', 'category', 'summary', and 'distance'
        """
        if self.index.ntotal == 0:
            if self.debug:
                print("  ⚠ Vector store is empty")
            return []
        
        if self.debug:
            print(f"  Searching for: {query[:50]}...")
        
        # Create embedding for query
        query_embedding = self.create_embeddings([query])
        
        # Search in FAISS
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        # Get results with metadata
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['distance'] = float(distance)
                result['rank'] = i + 1
                results.append(result)
        
        if self.debug:
            print(f"  ✓ Found {len(results)} results")
        
        return results
    
    def save(self, index_path: str, metadata_path: str):
        """
        Save FAISS index and metadata to disk
        
        Args:
            index_path: Path to save FAISS index
            metadata_path: Path to save metadata JSON
        """
        try:
            # Save FAISS index
            os.makedirs(os.path.dirname(index_path), exist_ok=True) if os.path.dirname(index_path) else None
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True) if os.path.dirname(metadata_path) else None
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            if self.debug:
                print(f"  ✓ Saved vector store to:")
                print(f"    Index: {index_path}")
                print(f"    Metadata: {metadata_path}")
                
        except Exception as e:
            print(f"  ✗ Error saving vector store: {e}")
            raise
    
    def load(self, index_path: str, metadata_path: str):
        """
        Load FAISS index and metadata from disk
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata JSON file
        """
        try:
            # Load FAISS index
            if not os.path.exists(index_path):
                raise FileNotFoundError(f"Index file not found: {index_path}")
            
            self.index = faiss.read_index(index_path)
            
            # Load metadata
            if not os.path.exists(metadata_path):
                raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            # Update dimension from loaded index
            self.dimension = self.index.d
        
            if self.debug:
                print(f"  ✓ Loaded vector store:")
                print(f"    Index: {index_path} ({self.index.ntotal} vectors)")
                print(f"    Metadata: {metadata_path} ({len(self.metadata)} entries)")
                
        except Exception as e:
            print(f"  ✗ Error loading vector store: {e}")
            raise


def load_labeled_json(file_path: str) -> List[Dict]:
    """
    Load labeled texts from JSON lines file
    
    Args:
        file_path: Path to JSON lines file
        
    Returns:
        List of dictionaries with 'summary', 'category', and 'text'
    """
    texts = []
    metadata_list = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                texts.append(data.get('text', ''))
                metadata_list.append({
                    'summary': data.get('summary', ''),
                    'category': data.get('category', 'world'),
                    'text': data.get('text', '')
                })
            except json.JSONDecodeError as e:
                print(f"  ⚠ Skipping invalid JSON line: {e}")
                continue
    
    return texts, metadata_list


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 50)
    print("Create Embeddings from Labeled JSON")
    print("=" * 50)
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(backend_dir, "data")
    
    # Input file
    input_file = os.path.join(data_dir, "labeled_test_post.json")
    
    if not os.path.exists(input_file):
        print(f"\n❌ File not found: {input_file}")
        print("   Please provide a valid JSON lines file path")
        sys.exit(1)
    
    print(f"\nInput file: {input_file}")
    
    try:
        # Load labeled texts
        print("\nStep 1: Loading labeled texts...")
        texts, metadata_list = load_labeled_json(input_file)
        
        if not texts:
            print("  ⚠ No texts found in file")
            sys.exit(1)
        
        print(f"  ✓ Loaded {len(texts)} labeled texts")
        for i, meta in enumerate(metadata_list[:3], 1):
            print(f"\n  Entry {i}:")
            print(f"    Category: {meta['category']}")
            print(f"    Summary: {meta['summary'][:60]}...")
        
        # Initialize embedding store
        print("\nStep 2: Initializing embedding store...")
        store = EmbeddingStore(debug=True)
        
        # Create embeddings and add to store
        print("\nStep 3: Creating embeddings...")
        store.add_texts(texts, metadata_list)
        
        # Save vector store
        print("\nStep 4: Saving vector store...")
        index_path = os.path.join(data_dir, "embeddings.index")
        metadata_path = os.path.join(data_dir, "embeddings_metadata.json")
        store.save(index_path, metadata_path)
        
        # Test search
        print("\nStep 5: Testing search...")
        test_query = "memory and reasoning"
        results = store.search(test_query, k=3)
        
        print(f"\nSearch results for: '{test_query}'")
        print("-" * 50)
        for result in results:
            print(f"\nRank {result['rank']} (distance: {result['distance']:.4f}):")
            print(f"  Category: {result['category']}")
            print(f"  Summary: {result['summary']}")
            print(f"  Text: {result['text'][:100]}...")
        
        print("\n" + "=" * 50)
        print("✓ Embeddings created and stored successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

