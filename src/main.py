from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict
from utils.scraping_utils import PlaywrightScraper
from database.mongo_db import MongoDBClient
from bson import json_util

import time
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RentalScraper:
    def __init__(self):
        load_dotenv()
        self.listings: List[Dict] = []
        self.scraper = PlaywrightScraper()
        self.mongo_client = MongoDBClient()
    
    def scrape_listings(self, url: str, start_date: str, end_date: str) -> None:
        """Main scraping method"""
        try:
            site, listings = self.scraper.scrape_page(url, start_date, end_date)
    
            if site == "none":
                print("Invalid URL. Scraping failed!")
                return

            self.save_to_json()
            self.mongo_client.insert_listings(listings, site)
            print("Scraping completed!")
            
        except Exception as e:
            logger.error(f"An error occurred while scraping: {str(e)}")
            raise
    
    def save_to_json(self, filename: str = None) -> None:
        """Save scraped data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"json_listings/{timestamp}.json"
        
        if self.listings:
            with open(filename, 'w', encoding='utf-8') as f:
                # Use json_util.dumps directly to handle MongoDB-specific types
                f.write(json_util.dumps(self.listings, indent=2))
            logger.info(f"Data saved to {filename}")
        else:
            logger.warning("No data to save")
    
    def close(self):
        """Close all connections"""
        if hasattr(self, 'mongo_client'):
            self.mongo_client.close()

def main() -> None:
    scraper = RentalScraper()
    
    try:
        # Example dates for the search
        start_date = "2025-03-05"
        end_date = "2025-03-07"
        
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date:
            search_start_date = current_date.strftime("%Y-%m-%d")
            search_end_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
            
            current_date += timedelta(days=1)
        
            # Construct the URL with the dates
            url = f'https://www.airbnb.com/s/Ger%C3%AAs--Portugal/homes?refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-02-01&monthly_length=3&monthly_end_date=2025-05-01&price_filter_input_type=0&channel=EXPLORE&query=Ger%C3%AAs&date_picker_type=calendar&checkin={search_start_date}&checkout={search_end_date}&source=structured_search_input_header&search_type=autocomplete_click&price_filter_num_nights=1&room_types%5B%5D=Entire%20home%2Fapt&selected_filter_order%5B%5D=room_types%3AEntire%20home%2Fapt&selected_filter_order%5B%5D=l2_property_type_ids%3A1&update_selected_filters=true&zoom_level=10&l2_property_type_ids%5B%5D=1&place_id=ChIJXTwMUMIYJQ0RMAqBT8DrAAo&location_bb=Qibr%2B8ECku1CJuk4wQKd%2Bg%3D%3D'
            scraper.scrape_listings(url, search_start_date, search_end_date)

            url = f'https://www.booking.com/searchresults.en-gb.html?ss=Geres&ssne=Geres&ssne_untouched=Geres&efdco=1&label=gen173nr-1BCAEoggI46AdIM1gEaLsBiAEBmAEJuAEZyAEM2AEB6AEBiAIBqAIDuAKMk5C8BsACAdICJGM2MDZhYjU5LTc2OTYtNDliZS1hZTA4LWJlMzVkNTRkMjJkYtgCBeACAQ&sid=6cc99139c41960236eadde3d7b3b1c9a&aid=304142&lang=en-gb&sb=1&src_elem=sb&src=index&dest_id=900040488&dest_type=city&checkin={search_start_date}&checkout={search_end_date}&group_adults=2&no_rooms=1&group_children=0'
            scraper.scrape_listings(url, search_start_date, search_end_date)
            time.sleep(10)
    finally:
        scraper.close()

    scraper = PlaywrightScraper()
    


    # search_listings = MongoDBClient().get_listings_by_date_range(start_date="2025-01-12", end_date="2025-01-18")

    # if not search_listings:
    #     logger.warning("No listings found for the specified date range")
    #     return
    
    # print("Listings found for the specified date range:")
    # for listing in search_listings:
    #     print(f"{listing['listing']['name']}: €{listing['listing']['price']}")

    # prediction = calculate_price_analyses(search_listings)
    # print("\nPrice Analysis:")
    # print(f"Average Price: €{prediction['average_price']}")
    # print(f"Highest Price: €{prediction['highest_price']}")
    # print(f"Lowest Price: €{prediction['lowest_price']}")
    # print(f"Total Listings: {prediction['total_listings']}")
    # print(f"Listings with Price > 0: {prediction['listings_with_price']}")


if __name__ == "__main__":
    main()