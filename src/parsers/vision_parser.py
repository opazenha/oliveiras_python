from google import genai
from google.genai import types
from dotenv import load_dotenv
from scrapers.hotels import Listing
from typing import List

import os
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def parse_listing_screenshot(image_path) -> List[Listing]:
    """Parse the screenshot using Vision AI"""
    try:
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Prepare the prompt
        prompt = """
        Analyze this Airbnb listing screenshot and extract ONLY the following information in JSON format for each listing on the image:
        - name: The listing title/name (required)
        - price: The price per night as a number only, no currency symbols (required)
        - rating: The rating score as a number (required)
        - bed_configuration: The bed setup details (optional)

        Example response:
        [
            {
                "name": "Cozy Studio in Downtown",
                "price": 150,
                "rating": 4.8,
                "bed_configuration": "1 queen bed"
            },
            {
                "name": "Spacious Suite with Balcony",
                "price": 250,
                "rating": 4.7,
                "bed_configuration": "2 queen beds"
            }
        ]

        Return ONLY the JSON array. If bed_configuration is not found for a listing, omit it from that listing's object.
        """

        # Read image file
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        # Implement exponential backoff retry logic
        base_delay = 5  # Start with 5 seconds delay
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to analyze image")
                response = client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type='image/png'
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        response_schema=Listing.get_json_schema()
                    )
                )
                
                # Process the response
                if response.text:
                    # Clean up the response text to ensure valid JSON
                    json_text = response.text.strip()
                    if not json_text.startswith('['):
                        json_start = json_text.find('[')
                        if json_start != -1:
                            json_text = json_text[json_start:]
                    if not json_text.endswith(']'):
                        json_end = json_text.rfind(']')
                        if json_end != -1:
                            json_text = json_text[:json_end+1]
                    
                    # Parse JSON and validate with Pydantic model
                    try:
                        data = json.loads(json_text)
                        listings = [Listing.model_validate(item) for item in data]
                        logger.info(f"Successfully parsed {len(listings)} listings")
                        return listings
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")
                        logger.debug(f"Raw JSON text: {json_text}")
                    except Exception as e:
                        logger.error(f"Failed to validate listing data: {e}")
                
                return []
            
            except Exception as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                if attempt < max_retries - 1:  # Don't wait after the last attempt
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All attempts failed. Last error: {str(e)}")
                    raise
        
        return []
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return []

if __name__ == "__main__":
    # Test the parser with a screenshot
    results = parse_listing_screenshot('listing_screenshot_20250108_152102.png')
    if results:
        print("\nParsed Listings Data:")
        for i, listing in enumerate(results, 1):
            print(f"\nListing {i}:")
            print(listing.model_dump_json(indent=2))