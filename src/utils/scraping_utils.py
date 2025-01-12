from playwright.sync_api import sync_playwright
from datetime import datetime
from PIL import Image
import numpy as np
from typing import Dict, Optional
from parsers.vision_parser import parse_listing_screenshot

import logging
import random
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlaywrightScraper:
    def __init__(self):
        # Common user agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        # Create screenshots directory if it doesn't exist
        self.screenshots_dir = "data/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Initialize browser session
        self.page = None
        self.first_visit = True
    
    def start_browser(self):
        """Initialize the browser with anti-detection measures"""
        if self.page is None:
            self.playwright = sync_playwright().start()
            
            # Configure browser to avoid detection
            browser = self.playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            context = browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True,
            )
            
            # Add custom scripts to mask automation
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.browser = browser
            self.context = context
            self.page = context.new_page()
        
        return self.page
    
    def close_browser(self):
        """Close all browser instances"""
        if hasattr(self, 'context'):
            self.context.close()
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        self.page = None
        self.first_visit = True
    
    def add_human_behavior(self, page):
        """Add random delays and mouse movements to simulate human behavior"""
        page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        page.wait_for_timeout(random.randint(1000, 2000))
        page.mouse.wheel(0, random.randint(300, 700))
        page.wait_for_timeout(random.randint(1000, 2000))
    
    def handle_cookie_consent(self, page) -> None:
        """Handle cookie consent banner if present"""
        try:
            # Look for common cookie consent button selectors
            cookie_selectors = [
                "button[data-testid='accept-btn']",
                "button:has-text('Accept')",
                "button:has-text('Accept all')",
                "button:has-text('Only necessary')",
                "[aria-label='Only necessary']",
                "#accept-cookies",
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_button = page.wait_for_selector(selector, timeout=5000)
                    if cookie_button:
                        logger.info(f"Found cookie consent button with selector: {selector}")
                        cookie_button.click()
                        page.wait_for_timeout(2000)  # Wait for banner to disappear
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not handle cookie consent: {str(e)}")
    
    def get_screenshot(self, page, selector: str, max_attempts: int = 3) -> Optional[str]:
        """Take a screenshot of the specified element with retry logic"""
        screenshot_path = None
        
        for attempt in range(max_attempts):
            logger.info(f"Screenshot attempt {attempt + 1}/{max_attempts}")
            
            try:
                # Wait for and get the site content
                element = page.wait_for_selector(selector, state='visible', timeout=60000)
                if element:
                    # More human-like behavior before screenshot
                    self.add_human_behavior(page)
                    
                    # Take a screenshot of the container
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    screenshot_filename = f"listing_screenshot_{timestamp}_attempt{attempt+1}.png"
                    screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
                    element.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved as {screenshot_path}")
                    
                    # Verify screenshot is not blank/white
                    img = Image.open(screenshot_path)
                    img_array = np.array(img)
                    
                    # Check if image is mostly white (threshold > 250)
                    if np.mean(img_array) > 250:
                        logger.warning("Screenshot appears to be blank/white, retrying...")
                        continue
                    
                    # If we get here, screenshot is valid
                    return screenshot_path
                else:
                    logger.warning("Element not found, retrying...")
            except TimeoutError:
                logger.error(f"Timeout on attempt {attempt + 1}")
                if attempt == max_attempts - 1:
                    raise
            
            # Wait between attempts
            page.wait_for_timeout(random.randint(3000, 5000))
            page.reload()
            self.add_human_behavior(page)
        
        return None
    
    def scrape_page(self, url: str, start_date: str, end_date: str) -> Optional[str | Dict]:
        """Scrape a page and return the screenshot path if successful"""
        try:
            page = self.start_browser()
            
            logger.info(f"Navigating to {url}")
            page.goto(url)
            
            # Initial wait and human-like behavior
            page.wait_for_timeout(5000)
            self.add_human_behavior(page)
            
            # Handle cookie consent only on first visit
            if self.first_visit:
                self.handle_cookie_consent(page)
                self.first_visit = False
            
            if "booking.com" in page.url:
                hotels = page.locator("//div[@data-testid='property-card']").all()
                print(f"Found {len(hotels)} hotels")
                listings = []
                for hotel in hotels:
                    hotel_dict = {}
                    hotel_dict['timestamp'] = datetime.now().isoformat()
                    hotel_dict['url'] = url
                    hotel_dict['start_date'] = start_date
                    hotel_dict['end_date'] = end_date
                    hotel_dict['name'] = hotel.locator("//div[@data-testid='title']").inner_text()
                    hotel_dict['price'] = hotel.locator("//span[@data-testid='price-and-discounted-price']").inner_text().replace(u'\xa0', u'')
                    hotel_dict['rating'] = hotel.locator("//div[@data-testid='review-score']").inner_text().split('\n')[1].strip()
                    hotel_dict['bed_configuration'] = hotel.locator("//div[@data-testid='recommended-units']").inner_text()
                    print(hotel_dict)
                    listings.append(hotel_dict)
                return "booking", listings

            if "airbnb" in page.url:
                screenshot_path = self.get_screenshot(page, "#site-content")
                # Parse the screenshot using Vision AI
                parsed_listings = parse_listing_screenshot(screenshot_path)
                if parsed_listings:
                    # Clear previous listings
                    self.listings = []
                    
                    # Store listings with metadata
                    for listing in parsed_listings:
                        self.listings.append({
                            'timestamp': datetime.now().isoformat(),
                            'url': url,
                            'start_date': start_date,
                            'end_date': end_date,
                            'listing': listing.model_dump()
                        })
                    logger.info(f"Successfully parsed {len(parsed_listings)} listings")
                return "airbnb", parsed_listings

            return "none", []
            
        except Exception as e:
            logger.error(f"An error occurred while scraping: {str(e)}")
            # Close browser on error to ensure clean state
            self.close_browser()
            raise