from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
from api.serp import SERPProfileSearcher
from api.twitter import TwitterScraper
from api.linkedin import LinkedInScraper
from api.instagram import InstagramScraper
from api.image import ImageSearcher
from api.articles import ArticleSearcher
from ai.categorise import TextLabeler
from ai.create_embeddings import EmbeddingStore, load_labeled_json
from ai.perspective import PerspectiveGenerator
from ai.instagram_analyzer import InstagramImageAnalyzer
from ai.prompt_summarise import PromptSummarizer
from ai.generator import ImageGenerator
from models.profile_state import ProfileState
import os
import re
import sys
import time

# Initialize FastAPI app
app = FastAPI(
    title="Profile Search API",
    description="API for searching LinkedIn, X (Twitter), and Instagram profiles using SERP",
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default port
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class SearchRequest(BaseModel):
    name: str
    top_n: Optional[int] = 2


class SearchResponse(BaseModel):
    name: str
    linkedin: Optional[Dict] = None
    twitter: Optional[Dict] = None
    instagram: Optional[Dict] = None
    image: Optional[Dict] = None
    articles: Optional[List[str]] = None


class ScrapeRequest(BaseModel):
    user_id: Optional[str] = None  # Twitter user ID
    linkedin_url: Optional[str] = None  # LinkedIn profile URL
    instagram_url: Optional[str] = None  # Instagram profile URL
    name: str  # Person's name (for filename)


class ScrapeResponse(BaseModel):
    success: bool
    message: str
    twitter_file: Optional[str] = None
    linkedin_file: Optional[str] = None
    twitter_count: Optional[int] = None
    linkedin_count: Optional[int] = None


class PerspectiveRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class PerspectiveResponse(BaseModel):
    perspective: str
    sources: List[Dict]
    query: str


class GenerateRequest(BaseModel):
    name: str
    number_of_images: Optional[int] = 3


class GenerateResponse(BaseModel):
    success: bool
    message: str
    prompt: Optional[str] = None
    generated_images: Optional[List[str]] = None  # List of filenames relative to public


@app.get("/")
async def root():
    return {
        "message": "Profile Search API",
        "version": "1.0.0",
            "endpoints": {
            "search": "/api/search-profiles",
            "scrape": "/api/scrape-profiles",
            "perspective": "/api/generate-perspective",
            "generate": "/api/generate",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.post("/api/search-profiles", response_model=SearchResponse)
async def search_profiles(request: SearchRequest):
    """
    Search for LinkedIn, X (Twitter), Instagram profiles, images, and articles for a given name
    
    Args:
        request: SearchRequest containing name and optional top_n
        
    Returns:
        SearchResponse with profile URLs, details, images, and articles
    """
    try:
        if not request.name or not request.name.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        
        # Initialize searcher (debug=True to see what's happening)
        print(f"\n{'='*60}", file=sys.stderr, flush=True)
        print(f"[API] Starting search for: {request.name}", file=sys.stderr, flush=True)
        print(f"{'='*60}\n", file=sys.stderr, flush=True)
        
        searcher = SERPProfileSearcher(debug=True)
        
        # Search for profiles
        results = searcher.search_all_profiles(
            name=request.name.strip(),
            top_n=request.top_n
        )
        
        # Small delay before image search
        time.sleep(1)
        
        # Search for images
        image_result = None
        try:
            image_searcher = ImageSearcher(debug=True)
            image_result = image_searcher.search_images(
                query=request.name.strip(),
                max_images=1
            )
            if image_result:
                print(f"[API] Image saved: {image_result.get('filename')}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[API] Error searching images: {e}", file=sys.stderr, flush=True)
            # Don't fail the whole request if image search fails
            image_result = None
        
        # Small delay before article search
        time.sleep(1)
        
        # Search for articles
        articles = None
        try:
            article_searcher = ArticleSearcher(debug=True)
            articles = article_searcher.search_articles(
                name=request.name.strip(),
                top_n=5
            )
            if articles:
                print(f"[API] Found {len(articles)} articles", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[API] Error searching articles: {e}", file=sys.stderr, flush=True)
            # Don't fail the whole request if article search fails
            articles = None
        
        # Log results for debugging - use stderr to ensure it shows
        
        
        # Save to centralized state object
        try:
            # Load existing state or create new one
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, "data")
            profile_state = ProfileState.load_from_file(request.name.strip(), data_dir)
            
            if profile_state is None:
                profile_state = ProfileState(name=request.name.strip())
            
            # Update with search results
            profile_state.update_search_results(
                linkedin=results.get("linkedin"),
                twitter=results.get("twitter"),
                instagram=results.get("instagram"),
                image=image_result,
                articles=articles if articles else None
            )
            
            # Save state to file
            state_file = profile_state.save_to_file(data_dir)
            print(f"[API] Profile state saved to: {state_file}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[API] Warning: Failed to save profile state: {e}", file=sys.stderr, flush=True)
            # Don't fail the request if state saving fails
        
        return SearchResponse(
            name=results.get("name", request.name),
            linkedin=results.get("linkedin"),
            twitter=results.get("twitter"),
            instagram=results.get("instagram"),
            image=image_result,
            articles=articles if articles else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while searching: {str(e)}"
        )


def parse_tweets_file(file_path: str) -> List[str]:
    """
    Parse tweets from text file (one tweet per line)
    
    Args:
        file_path: Path to tweets text file
        
    Returns:
        List of tweet texts
    """
    texts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                text = line.strip()
                if text and len(text) > 10:  # Filter out very short lines
                    texts.append(text)
    except Exception as e:
        print(f"Error parsing tweets file: {e}")
    return texts



def parse_linkedin_file(file_path: str) -> List[str]:
    """
    Parse LinkedIn posts from text file
    
    Args:
        file_path: Path to LinkedIn posts text file
        
    Returns:
        List of post texts
    """
    texts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Split by post separators
            posts = content.split('Post ')
            
            for post in posts[1:]:  # Skip first part (header)
                # Extract text between "Text:" and next separator
                if 'Text:' in post:
                    text_start = post.find('Text:') + len('Text:')
                    # Find the next separator line
                    text_end = post.find('\n' + '=' * 80, text_start)
                    if text_end == -1:
                        text_end = len(post)
                    
                    text = post[text_start:text_end].strip()
                    if text and len(text) > 10:
                        texts.append(text)
    except Exception as e:
        print(f"Error parsing LinkedIn file: {e}")
    return texts









@app.post("/api/scrape-profiles", response_model=ScrapeResponse)
async def scrape_profiles(request: ScrapeRequest):
    """
    Scrape tweets and LinkedIn posts for a given profile
    
    Args:
        request: ScrapeRequest containing user_id (Twitter), linkedin_url, and name
        
    Returns:
        ScrapeResponse with file paths and counts
    """
    if not request.user_id and not request.linkedin_url and not request.instagram_url:
        raise HTTPException(
            status_code=400,
            detail="At least one of user_id (Twitter), linkedin_url, or instagram_url must be provided"
        )
    
    # Sanitize name for filename
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', request.name.strip())
    
    # Load existing profile state or create new one
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    profile_state = ProfileState.load_from_file(request.name.strip(), data_dir)
    
    if profile_state is None:
        profile_state = ProfileState(name=request.name.strip())
        print(f"[API] Created new profile state for: {request.name}", file=sys.stderr, flush=True)
    else:
        print(f"[API] Loaded existing profile state for: {request.name}", file=sys.stderr, flush=True)
    
    results = {
        "success": True,
        "message": "Scraping completed",
        "twitter_file": None,
        "linkedin_file": None,
        "twitter_count": 0,
        "linkedin_count": 0
    }
    
    errors = []

    
    
    # Scrape Twitter/X posts if user_id is provided
    if request.user_id:
        try:
            twitter_scraper = TwitterScraper(debug=False)
            tweets = twitter_scraper.get_user_posts_by_id(request.user_id, max_results=5)
            
            if tweets:
                # Create data directory if it doesn't exist
                script_dir = os.path.dirname(os.path.abspath(__file__))
                data_dir = os.path.join(script_dir, "data")
                os.makedirs(data_dir, exist_ok=True)
                
                # Save tweets to file
                twitter_filename = f"tweets_{safe_name}_{request.user_id}.txt"
                twitter_file = os.path.join(data_dir, twitter_filename)
                twitter_scraper.save_tweets_to_file(tweets, twitter_file, format='text')
                # Return relative path from backend directory
                results["twitter_file"] = f"data/{twitter_filename}"
                results["twitter_count"] = len(tweets)
                
                # Update profile state with scraped tweets
                profile_state.update_scraped_content(twitter_posts=tweets)
            else:
                errors.append("No tweets found for the provided user_id")
                
        except Exception as e:
            errors.append(f"Twitter scraping error: {str(e)}")
    
    # Scrape LinkedIn posts if linkedin_url is provided
    if request.linkedin_url:
        linkedin_scraper = None
        try:
            # Initialize LinkedIn scraper (headless=True for server use)
            linkedin_scraper = LinkedInScraper(headless=False, debug=True)
            
            # Login to LinkedIn
            login_success = linkedin_scraper.login()
            if not login_success:
                errors.append("LinkedIn login failed. Please check credentials.")
            else:
                # Scrape posts (20 posts as requested)
                posts = linkedin_scraper.get_user_posts(request.linkedin_url, max_posts=20)
                
                if posts:
                    # Create data directory if it doesn't exist
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    data_dir = os.path.join(script_dir, "data")
                    os.makedirs(data_dir, exist_ok=True)
                    
                    # Extract username from LinkedIn URL for filename
                    linkedin_username = request.linkedin_url.rstrip('/').split('/')[-1]
                    linkedin_filename = f"linkedin_posts_{safe_name}_{linkedin_username}.txt"
                    linkedin_file = os.path.join(data_dir, linkedin_filename)
                    linkedin_scraper.save_posts_to_file(posts, linkedin_file, request.linkedin_url)
                    # Return relative path from backend directory
                    results["linkedin_file"] = f"data/{linkedin_filename}"
                    results["linkedin_count"] = len(posts)
                    
                    # Update profile state with scraped LinkedIn posts
                    profile_state.update_scraped_content(linkedin_posts=posts)
                else:
                    errors.append("No LinkedIn posts found")
                    
        except Exception as e:
            errors.append(f"LinkedIn scraping error: {str(e)}")
        finally:
            # Always close the browser
            if linkedin_scraper:
                try:
                    linkedin_scraper.close()
                except:
                    pass
    
    # Scrape Instagram photos if instagram_url is provided
    if request.instagram_url:
        instagram_scraper = None
        try:
            # Initialize Instagram scraper
            instagram_scraper = InstagramScraper(headless=False, debug=True)
            
            # Try to login (optional - may work without login for public profiles)
            try:
                login_success = instagram_scraper.login()
                if not login_success:
                    print("[API] Instagram login failed, attempting direct access", file=sys.stderr, flush=True)
            except:
                print("[API] Instagram login skipped, attempting direct access", file=sys.stderr, flush=True)
            
            # Scrape photos (20 photos as requested)
            photos = instagram_scraper.get_profile_photos(request.instagram_url, max_photos=20)
            
            if photos:
                # Create data directory if it doesn't exist
                script_dir = os.path.dirname(os.path.abspath(__file__))
                data_dir = os.path.join(script_dir, "data")
                os.makedirs(data_dir, exist_ok=True)
                
                # Extract username from Instagram URL for filename
                instagram_username = request.instagram_url.rstrip('/').split('/')[-1]
                instagram_filename = f"instagram_photos_{safe_name}_{instagram_username}.txt"
                instagram_file = os.path.join(data_dir, instagram_filename)
                instagram_scraper.save_photos_to_file(photos, instagram_file, request.instagram_url)
                # Return relative path from backend directory
                results["instagram_file"] = f"data/{instagram_filename}"
                results["instagram_count"] = len(photos)
                
                # Update profile state with scraped Instagram photos
                profile_state.update_scraped_content(instagram_photos=photos)
                
                # Analyze Instagram photos using InstagramImageAnalyzer
                try:
                    print(f"[API] Starting Instagram photo analysis...", file=sys.stderr, flush=True)
                    analyzer = InstagramImageAnalyzer(debug=True)
                    
                    # Analyze the photos directly (they're already in the right format from scraper)
                    # The photos list from InstagramScraper has: url, image_url, caption, timestamp, etc.
                    analysis_result = analyzer.analyze_profile_photos(photos, max_photos=20)
                    
                    # Update profile state with analysis
                    profile_state.update_instagram_analysis(analysis_result)
                    
                    print(f"[API] Instagram analysis completed: {analysis_result.get('total_photos_analyzed', 0)} photos analyzed", file=sys.stderr, flush=True)
                    if analysis_result.get('summary'):
                        summary_preview = analysis_result['summary'][:200] if len(analysis_result['summary']) > 200 else analysis_result['summary']
                        print(f"[API] Summary preview: {summary_preview}...", file=sys.stderr, flush=True)
                    
                except Exception as e:
                    print(f"[API] Warning: Instagram photo analysis failed: {e}", file=sys.stderr, flush=True)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    # Don't fail the whole request if analysis fails
                    errors.append(f"Instagram analysis error: {str(e)}")
            else:
                errors.append("No Instagram photos found")
                
        except Exception as e:
            errors.append(f"Instagram scraping error: {str(e)}")
        finally:
            # Always close the browser
            if instagram_scraper:
                try:
                    instagram_scraper.close()
                except:
                    pass
    
    # Save updated profile state with scraped content
    try:
        state_file = profile_state.save_to_file(data_dir)
        print(f"[API] Profile state updated and saved to: {state_file}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[API] Warning: Failed to save profile state: {e}", file=sys.stderr, flush=True)
    
    # Step: Parse scraped files and collect texts for categorization
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    all_texts = []
    
    # Parse Twitter file if it exists
    if results.get("twitter_file"):
        twitter_file_path = os.path.join(script_dir, results["twitter_file"])
        if os.path.exists(twitter_file_path):
            twitter_texts = parse_tweets_file(twitter_file_path)
            all_texts.extend(twitter_texts)
    
    # Parse LinkedIn file if it exists
    if results.get("linkedin_file"):
        linkedin_file_path = os.path.join(script_dir, results["linkedin_file"])
        if os.path.exists(linkedin_file_path):
            linkedin_texts = parse_linkedin_file(linkedin_file_path)
            all_texts.extend(linkedin_texts)
    
    # Categorize and create embeddings if we have texts
    if all_texts:
        try:
            # Initialize labeler
            labeler = TextLabeler(debug=False)
            
            # Categorize all texts
            labeled_texts = labeler.label_texts(all_texts)
            
            # Save categorized texts to JSON
            labeled_json_path = os.path.join(data_dir, f"labeled_{safe_name}.json")
            labeler.save_labeled_texts(labeled_texts, labeled_json_path, format='json')
            
            # Create/load embeddings store
            embedding_store = EmbeddingStore(debug=False)
            index_path = os.path.join(data_dir, "embeddings.index")
            metadata_path = os.path.join(data_dir, "embeddings_metadata.json")
            
            # Load existing embeddings if they exist
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                try:
                    embedding_store.load(index_path, metadata_path)
                except Exception as e:
                    print(f"Could not load existing embeddings, creating new: {e}")
            
            # Prepare texts and metadata for embedding
            texts_for_embedding = [lt['text'] for lt in labeled_texts]
            metadata_for_embedding = [
                {
                    'summary': lt['summary'],
                    'category': lt['category'],
                    'text': lt['text']
                }
                for lt in labeled_texts
            ]
            
            # Add to embedding store
            embedding_store.add_texts(texts_for_embedding, metadata_for_embedding)
            
            # Save embeddings
            embedding_store.save(index_path, metadata_path)
            
            results["message"] += f" | Categorized {len(labeled_texts)} posts and created embeddings"
            
        except Exception as e:
            error_msg = f"Categorization/embedding error: {str(e)}"
            errors.append(error_msg)
            results["message"] += f" | Warning: Failed to categorize/embed: {str(e)}"
    
    # Set success status and message
    if errors and results["twitter_count"] == 0 and results["linkedin_count"] == 0:
        results["success"] = False
        results["message"] = "; ".join(errors)
    elif errors:
        results["message"] = f"Partially completed. Errors: {'; '.join(errors)}"
    
    return ScrapeResponse(**results)


@app.post("/api/generate-perspective", response_model=PerspectiveResponse)
async def generate_perspective(request: PerspectiveRequest):
    """
    Generate a perspective/answer based on a user query using RAG
    
    Args:
        request: PerspectiveRequest containing query and optional top_k
        
    Returns:
        PerspectiveResponse with perspective, sources, and query
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Get paths to vector store files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, "data")
        index_path = os.path.join(data_dir, "embeddings.index")
        metadata_path = os.path.join(data_dir, "embeddings_metadata.json")
        
        # Check if vector store exists
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            raise HTTPException(
                status_code=404,
                detail="Vector store not found. Please scrape and categorize posts first."
            )
        
        # Try to load profile state to get text persona prompt
        # We'll try to find the most recent state file
        text_persona_prompt = None
        try:
            import glob
            state_files = glob.glob(os.path.join(data_dir, "profile_state_*.json"))
            if state_files:
                # Use the most recently modified state file
                latest_state_file = max(state_files, key=os.path.getmtime)
                # Extract name from filename
                state_name = os.path.basename(latest_state_file).replace("profile_state_", "").replace(".json", "")
                profile_state = ProfileState.load_from_file(state_name, data_dir)
                if profile_state and profile_state.text_prompt:
                    text_persona_prompt = profile_state.text_prompt
                    print(f"[API] Using text persona prompt from state: {text_persona_prompt[:50]}...", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[API] Warning: Could not load text persona prompt from state: {e}", file=sys.stderr, flush=True)
        
        # Initialize perspective generator
        generator = PerspectiveGenerator(debug=False)
        
        # Load vector store
        generator.load_vector_store(index_path, metadata_path)
        
        # Generate perspective with optional persona prompt
        result = generator.search_and_generate_perspective(
            query=request.query.strip(),
            top_k=request.top_k,
            persona_prompt=text_persona_prompt
        )
        
        return PerspectiveResponse(
            perspective=result['perspective'],
            sources=result['sources'],
            query=result['query']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating perspective: {str(e)}"
        )


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_images(request: GenerateRequest):
    """
    Generate images based on Instagram summary and saved profile image
    
    Args:
        request: GenerateRequest containing name and optional number_of_images
        
    Returns:
        GenerateResponse with generated image filenames
    """
    try:
        if not request.name or not request.name.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        
        # Get paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, "data")
        frontend_dir = os.path.dirname(script_dir)  # Go up one level from backend
        frontend_public_dir = os.path.join(frontend_dir, "frontend", "public")
        
        # Create safe name for file lookup
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', request.name.strip())
        
        # Load profile state
        profile_state = ProfileState.load_from_file(safe_name, data_dir)
        if not profile_state:
            raise HTTPException(
                status_code=404,
                detail=f"Profile state not found for {request.name}. Please search and scrape first."
            )
        
        # Check if Instagram analysis exists
        if not profile_state.instagram_analysis or not profile_state.instagram_analysis.get('summary'):
            raise HTTPException(
                status_code=404,
                detail="Instagram analysis not found. Please scrape Instagram photos first."
            )
        
        # Check if profile image exists
        if not profile_state.image or not profile_state.image.get('filename'):
            raise HTTPException(
                status_code=404,
                detail="Profile image not found. Please search profiles first."
            )
        
        # Get Instagram summary
        instagram_summary = profile_state.instagram_analysis['summary']
        person_name = profile_state.name
        image_filename = profile_state.image['filename']
        
        # Convert image filename to absolute path
        # Image filename is relative to frontend/public, e.g., "carl_pei.jpg"
        image_path = os.path.join(frontend_public_dir, image_filename)
        
        if not os.path.exists(image_path):
            raise HTTPException(
                status_code=404,
                detail=f"Profile image file not found: {image_filename}"
            )
        
        print(f"[API] Generating images for {person_name}...", file=sys.stderr, flush=True)
        print(f"[API] Using Instagram summary: {instagram_summary[:100]}...", file=sys.stderr, flush=True)
        print(f"[API] Using base image: {image_path}", file=sys.stderr, flush=True)
        
        # Step 1: Create text persona prompt and save to state
        prompt_summarizer = PromptSummarizer(debug=True)
        
        # Generate text persona prompt for LLM
        text_persona_prompt = prompt_summarizer.text_prompt(
            character_summary=instagram_summary,
            person_name=person_name
        )
        
        if text_persona_prompt:
            profile_state.update_text_prompt(text_persona_prompt)
            print(f"[API] Generated text persona prompt: {text_persona_prompt}", file=sys.stderr, flush=True)
            # Save state with text prompt
            profile_state.save_to_file(data_dir)
        else:
            print(f"[API] Warning: Failed to generate text persona prompt", file=sys.stderr, flush=True)
        
        # Step 2: Create multiple different image prompts from Instagram summary
        number_of_images = request.number_of_images or 3
        
        image_prompts = prompt_summarizer.create_multiple_image_prompts(
            character_summary=instagram_summary,
            person_name=person_name,
            num_prompts=number_of_images
        )
        
        if not image_prompts or len(image_prompts) < number_of_images:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate {number_of_images} image prompts from Instagram summary"
            )
        
        print(f"[API] Generated {len(image_prompts)} different prompts:", file=sys.stderr, flush=True)
        for i, prompt in enumerate(image_prompts, 1):
            print(f"[API] Prompt {i}: {prompt}", file=sys.stderr, flush=True)
        
        # Step 3: Generate images using ImageGenerator - one image per prompt
        image_generator = ImageGenerator(debug=True)
        generated_filenames = []
        all_prompts_used = []
        
        for i, image_prompt in enumerate(image_prompts[:number_of_images], 1):
            try:
                print(f"[API] Generating image {i}/{number_of_images} with unique prompt...", file=sys.stderr, flush=True)
                
                # Generate one image per prompt for variety
                generation_result = image_generator.generate_image(
                    prompt=image_prompt,
                    subject_reference=image_path,
                    aspect_ratio="3:4",
                    number_of_images=1,  # Generate one image per prompt
                    prompt_optimizer=True
                )
                
                if not generation_result or not generation_result.get('image_urls'):
                    print(f"[API] Warning: Failed to generate image {i}", file=sys.stderr, flush=True)
                    continue
                
                # Step 4: Download and save generated image to frontend/public
                image_url = generation_result['image_urls'][0]  # Get the first (and only) image
                
                try:
                    # Create filename based on person name and index
                    file_extension = "png"  # Default extension
                    if "." in image_url:
                        # Try to get extension from URL
                        url_ext = image_url.split(".")[-1].split("?")[0].lower()
                        if url_ext in ["jpg", "jpeg", "png", "webp"]:
                            file_extension = url_ext
                    
                    generated_filename = f"{safe_name}_generated_{i}.{file_extension}"
                    output_path = os.path.join(frontend_public_dir, generated_filename)
                    
                    # Download and save image
                    success = image_generator.save_image(image_url, output_path)
                    
                    if success:
                        generated_filenames.append(generated_filename)
                        all_prompts_used.append(image_prompt)
                        print(f"[API] Saved generated image {i}: {generated_filename}", file=sys.stderr, flush=True)
                    else:
                        print(f"[API] Warning: Failed to save image {i}", file=sys.stderr, flush=True)
                        
                except Exception as e:
                    print(f"[API] Error saving image {i}: {e}", file=sys.stderr, flush=True)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    
            except Exception as e:
                print(f"[API] Error generating image {i}: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc(file=sys.stderr)
                continue
        
        # All images generated with unique prompts
        
        if not generated_filenames:
            raise HTTPException(
                status_code=500,
                detail="Failed to save any generated images"
            )
        
        # Combine all prompts into a single string for the response
        combined_prompts = "\n\n".join([f"Prompt {i+1}: {p}" for i, p in enumerate(all_prompts_used)])
        
        return GenerateResponse(
            success=True,
            message=f"Successfully generated {len(generated_filenames)} unique image(s)",
            prompt=combined_prompts,
            generated_images=generated_filenames
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error in generate endpoint: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating images: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True  # Auto-reload on code changes
    )

