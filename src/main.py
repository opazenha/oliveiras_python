from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict
from utils.scraping_utils import PlaywrightScraper
from database.mongo_db import MongoDBClient
from bson import json_util
from scrapers.airbnb import calculate_airbnb_price_analyses
from scrapers.booking import calculate_booking_price_analyses

import asyncio
import logging
import argparse

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RentalScraper:
    def __init__(self):
        load_dotenv()
        self.listings: List[Dict] = []
        self.airbnb_scraper = PlaywrightScraper()
        self.booking_scraper = PlaywrightScraper()
        self.mongo_client = MongoDBClient()
    
    async def scrape_listings(self, url: str, start_date: str, end_date: str, scraper: PlaywrightScraper) -> None:
        """Main scraping method"""
        try:
            site, listings = await scraper.scrape_page(url, start_date, end_date)
    
            if site == "none":
                print("Invalid URL. Scraping failed!")
                return

            self.save_to_json()
            self.mongo_client.insert_listings(listings, site)
            print(f"Scraping completed for {site}!")
            
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
    
    async def close(self):
        """Close all connections"""
        if hasattr(self, 'mongo_client'):
            self.mongo_client.close()

async def main() -> None:
    parser = argparse.ArgumentParser(description='Scrape rental listings')
    parser.add_argument('start_date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('end_date', type=str, help='End date in YYYY-MM-DD format')
    args = parser.parse_args()

    scraper = RentalScraper()
    
    try:
        start_date = args.start_date
        end_date = args.end_date
        
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date:
            search_start_date = current_date.strftime("%Y-%m-%d")
            search_end_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
            
            current_date += timedelta(days=1)
        
            # Construct the URLs
            airbnb_url = f'https://www.airbnb.com/s/Ger%C3%AAs--Portugal/homes?refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-02-01&monthly_length=3&monthly_end_date=2025-05-01&price_filter_input_type=0&channel=EXPLORE&query=Ger%C3%AAs&date_picker_type=calendar&checkin={search_start_date}&checkout={search_end_date}&source=structured_search_input_header&search_type=autocomplete_click&price_filter_num_nights=1&room_types%5B%5D=Entire%20home%2Fapt&selected_filter_order%5B%5D=room_types%3AEntire%20home%2Fapt&selected_filter_order%5B%5D=l2_property_type_ids%3A1&update_selected_filters=true&zoom_level=10&l2_property_type_ids%5B%5D=1&place_id=ChIJXTwMUMIYJQ0RMAqBT8DrAAo&location_bb=Qibr%2B8ECku1CJuk4wQKd%2Bg%3D%3D'
            booking_url = f'https://www.booking.com/searchresults.en-gb.html?label=gen173nr-1BCAEoggI46AdIM1gEaLsBiAEBmAEJuAEZyAEM2AEB6AEBiAIBqAIDuAKMk5C8BsACAdICJGM2MDZhYjU5LTc2OTYtNDliZS1hZTA4LWJlMzVkNTRkMjJkYtgCBeACAQ&sid=6cc99139c41960236eadde3d7b3b1c9a&aid=304142&ss=Geres&ssne=Geres&ssne_untouched=Geres&efdco=1&lang=en-gb&src=index&dest_id=900040488&dest_type=city&checkin={search_start_date}&checkout={search_end_date}&group_adults=2&no_rooms=1&group_children=0&nflt=privacy_type%3D3'
            # Run both scrapers concurrently
            await asyncio.gather(
                scraper.scrape_listings(airbnb_url, search_start_date, search_end_date, scraper.airbnb_scraper),
                scraper.scrape_listings(booking_url, search_start_date, search_end_date, scraper.booking_scraper)
            )
            
            await asyncio.sleep(10)
    finally:
        await scraper.airbnb_scraper.close_browser()
        await scraper.booking_scraper.close_browser()
        await scraper.close()

    airbnb_listings = MongoDBClient().get_airbnb_listings_by_date_range(start_date, end_date)
    if airbnb_listings:
        print("\nAirbnb Listings Data:")
        print(calculate_airbnb_price_analyses(airbnb_listings))
    else:
        print("No airbnb listings found.")

    booking_listings = MongoDBClient().get_booking_listings_by_date_range(start_date, end_date)
    if booking_listings:
        print("\nBooking Listings Data:")
        print(calculate_booking_price_analyses(booking_listings))
    else:
        print("No booking listings found.")

if __name__ == "__main__":
    asyncio.run(main())