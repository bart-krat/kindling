The core functionality of this kindling repo is to codify a person's views from the internet and represent by a RAG based llm.

The UI which is run via next.js and is connected to a python backend via FASTAPI. 


OVERVIEW

To begin the flow, the user can choose a person/founder of interest and click the Search button. This will use various SERP API endpoints to return 
social media profiles, articles and a base image for the person of interest. The decision to keep this programmatic is that the SERP API effectively uses 
google along with some filtering to return results. A search agent here in my opinion would have been overkill.

Once the relevant search results have been returned the next step is to scrape the relevant profiles of the person of interest. Twitter (X) had an easy 
enough api to use to extract posts, however LinkedIn and Instagram required browser scraping due to the platforms automation protection. For this case I 
used Selenium which programmatically scanned the various fields to return the users posts. A browsing agent here was a little more enticing however 
the programmatic field scanning was effective enough.

To minimise the need for more buttons and simplify the user journey; once the profiles had been scraped the data is further processed by both computer vision
and natural language processing. This in hand takes the founder's linkedin and X posts to be put in to embeddings whereas a collection of their instagram 
photos would be summarised as a whole to gain a holistic understanding of the founder.

Now that we have processed what data information we can find about the founder we can now generate output which will capture their unique essence. 
From the embeddings and consolidated text summary of their instagram we can ask questions about their perspective on the world. In addition from their base 
image and secondary image summary we can generate new images of our founder to tell their story.


BACKEND ARCHITECTURE

The backend server which has the entry point of main.py has a microservices architecture. 

I have made two main subdirectories api and ai for core functionality along with the model directory which has the logic for the centralized state object 
which is used for tracking, visibility and durability.

The api directory has all the functionality for the SERP API and Scraping techniques.
The ai directory has all the functionality for summarizing, categorizing, embedding and generating new content.

Using microservices architecture here has allowed me to get the benefits of object orientated programming where I can isolate the various methods. 

However when setting up the FASTAPI I limited it to four core functional endpoints. This was an attempt to keep the similar behaviour of the application 
within these endpoints and follow the general user flow. Consequently this meant that there were multiple methods being triggered within a single endpoint. 
Using conditional if statements and optional parameters meant that i was still able to isolate and test the sub methods within these endpoints as 
can be seen in the test directory. These choices therefore reflect a balance between maintainability and modularity.


Key System Requirements:

Python = 3.12 for replicate
GoogleC Chrome
ChromeDriver for MacOS
Node.js 18+
Python Virtual Environment
Install Requirements.txt
Npm Install


Environment Variables:

   # OpenAI (required for AI features)
   OPENAI_API_KEY=your_openai_api_key
   
   # DataForSEO (required for search)
   DATAFORSEO_LOGIN=your_dataforseo_login
   DATAFORSEO_PASSWORD=your_dataforseo_password
   
   # Twitter/X (required for Twitter scraping)
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   
   # Replicate (required for image generation)
   REPLICATE_API_TOKEN=your_replicate_api_token
   
   # LinkedIn (required for LinkedIn scraping)
   LINKEDIN_EMAIL=your_linkedin_email
   LINKEDIN_PASSWORD=your_linkedin_password
   
   # Instagram (optional, for Instagram scraping)
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password











