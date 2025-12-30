"""
Profile State Model - Centralized state object for storing profile search and scraped data
"""
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import json
import os
from pathlib import Path


class ProfileState(BaseModel):
    """Centralized state object for a person's profile data"""
    name: str
    timestamp: datetime = datetime.now()
    
    # Search results - all URLs discovered
    linkedin: Optional[Dict] = None  # { profile_url, all_urls }
    twitter: Optional[Dict] = None  # { profile_url, all_urls, username, user_id }
    instagram: Optional[Dict] = None  # { profile_url, all_urls }
    image: Optional[Dict] = None  # { filename, url, title, source }
    articles: Optional[List[str]] = None  # List of article URLs
    
    # Scraped content
    linkedin_posts: Optional[List[Dict]] = None
    twitter_posts: Optional[List[Dict]] = None
    instagram_photos: Optional[List[Dict]] = None
    
    # Processed/analyzed content
    instagram_analysis: Optional[Dict] = None  # { summary, individual_analyses, total_photos_analyzed }
    
    # Metadata
    search_completed: bool = False
    scrape_completed: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def load_from_file(cls, name: str, data_dir: str = "data") -> Optional['ProfileState']:
        """
        Load profile state from JSON file
        
        Args:
            name: Person's name (will be sanitized for filename)
            data_dir: Directory where state files are stored
            
        Returns:
            ProfileState object or None if file doesn't exist
        """
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip())
        state_file = os.path.join(data_dir, f"profile_state_{safe_name}.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert timestamp string back to datetime
                    if 'timestamp' in data and isinstance(data['timestamp'], str):
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    return cls(**data)
            except Exception as e:
                print(f"Error loading profile state: {e}")
                return None
        return None
    
    def save_to_file(self, data_dir: str = "data") -> str:
        """
        Save profile state to JSON file
        
        Args:
            data_dir: Directory where state files should be stored
            
        Returns:
            Path to saved file
        """
        import re
        os.makedirs(data_dir, exist_ok=True)
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', self.name.strip())
        state_file = os.path.join(data_dir, f"profile_state_{safe_name}.json")
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(self.dict(), f, indent=2, ensure_ascii=False, default=str)
        
        return state_file
    
    def update_search_results(
        self,
        linkedin: Optional[Dict] = None,
        twitter: Optional[Dict] = None,
        instagram: Optional[Dict] = None,
        image: Optional[Dict] = None,
        articles: Optional[List[str]] = None
    ):
        """Update search results in state"""
        if linkedin is not None:
            self.linkedin = linkedin
        if twitter is not None:
            self.twitter = twitter
        if instagram is not None:
            self.instagram = instagram
        if image is not None:
            self.image = image
        if articles is not None:
            self.articles = articles
        self.search_completed = True
    
    def update_scraped_content(
        self,
        linkedin_posts: Optional[List[Dict]] = None,
        twitter_posts: Optional[List[Dict]] = None,
        instagram_photos: Optional[List[Dict]] = None
    ):
        """Update scraped content in state"""
        if linkedin_posts is not None:
            self.linkedin_posts = linkedin_posts
        if twitter_posts is not None:
            self.twitter_posts = twitter_posts
        if instagram_photos is not None:
            self.instagram_photos = instagram_photos
        self.scrape_completed = True
    
    def update_instagram_analysis(self, analysis: Dict):
        """Update Instagram photo analysis in state"""
        self.instagram_analysis = analysis

