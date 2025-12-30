# API Test Scripts

This directory contains individual test scripts for each sub-method within the API endpoints.

## Prerequisites

1. Make sure the FastAPI server is running:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. Ensure you have the `requests` library installed:
   ```bash
   pip install requests
   ```

## Test Scripts

### Search Endpoints (`/api/search-profiles`)

- **`test_search_linkedin.py`** - Tests LinkedIn profile search
- **`test_search_twitter.py`** - Tests Twitter/X profile search
- **`test_search_instagram.py`** - Tests Instagram profile search
- **`test_search_images.py`** - Tests profile image search
- **`test_search_articles.py`** - Tests article search

### Scrape Endpoints (`/api/scrape-profiles`)

- **`test_scrape_twitter.py`** - Tests Twitter/X post scraping
- **`test_scrape_linkedin.py`** - Tests LinkedIn post scraping
- **`test_scrape_instagram.py`** - Tests Instagram photo scraping

### Other Endpoints

- **`test_generate_perspective.py`** - Tests perspective generation (`/api/generate-perspective`)
- **`test_generate_images.py`** - Tests image generation (`/api/generate`)

## Usage

Run any test script individually:

```bash
# From the backend directory
python tests/test_scrape_twitter.py
python tests/test_search_linkedin.py
python tests/test_generate_perspective.py
```

Or make them executable and run directly:

```bash
chmod +x tests/*.py
./tests/test_scrape_twitter.py
```

## Test Data

Most tests use "Carl Pei" as the test subject with the following identifiers:
- Twitter User ID: `41777199`
- LinkedIn URL: `https://uk.linkedin.com/in/getpeid`
- Instagram URL: `https://www.instagram.com/getpeid/`

You can modify the test scripts to use different test data as needed.

## Notes

- **Scraping tests** (LinkedIn, Instagram) may take several minutes and may open browser windows
- **Image generation test** requires:
  1. Profile state to exist
  2. Instagram analysis to be completed
  3. Profile image from search
- All tests include proper error handling and timeout settings

