from playwright.async_api import async_playwright, Page
from datetime import datetime
from PIL import Image
import numpy as np
from typing import Dict, Optional, Tuple, List
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
        self.browser = None
        self.context = None
        self.page = None
        self.first_visit = True

    async def start_browser(self) -> Page:
        """Initialize the browser with anti-detection measures"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # Set to False to avoid detection
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            self.context = await self.browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True,
            )
            
            # Add custom scripts to mask automation
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.page = await self.context.new_page()
        return self.page

    async def close_browser(self):
        """Close all browser instances"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None

    async def add_human_behavior(self, page: Page):
        """Add random delays and mouse movements to simulate human behavior"""
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await page.wait_for_timeout(random.randint(1000, 2000))
        await page.mouse.wheel(0, random.randint(300, 700))
        await page.wait_for_timeout(random.randint(1000, 2000))

    async def handle_cookie_consent(self, page: Page):
        """Handle cookie consent banner if present"""
        try:
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
                    cookie_button = await page.wait_for_selector(selector, timeout=5000)
                    if cookie_button:
                        logger.info(f"Found cookie consent button with selector: {selector}")
                        await cookie_button.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not handle cookie consent: {str(e)}")

    async def get_screenshot(self, page: Page, selector: str, max_attempts: int = 3) -> Optional[str]:
        """Take a screenshot of the specified element with retry logic"""
        screenshot_path = None
        
        for attempt in range(max_attempts):
            logger.info(f"Screenshot attempt {attempt + 1}/{max_attempts}")
            
            try:
                element = await page.wait_for_selector(selector, state='visible', timeout=60000)
                if element:
                    await self.add_human_behavior(page)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    screenshot_filename = f"listing_screenshot_{timestamp}_attempt{attempt+1}.png"
                    screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
                    await element.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved as {screenshot_path}")
                    
                    # Verify screenshot is not blank/white
                    img = Image.open(screenshot_path)
                    img_array = np.array(img)
                    
                    if np.mean(img_array) > 250:
                        logger.warning("Screenshot appears to be blank/white, retrying...")
                        continue
                    
                    return screenshot_path
                else:
                    logger.warning("Element not found, retrying...")
            except Exception as e:
                logger.error(f"Screenshot attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    raise
            
            await page.wait_for_timeout(random.randint(3000, 5000))
            await page.reload()
            await self.add_human_behavior(page)
        
        return None

    async def scrape_page(self, url: str, start_date: str, end_date: str) -> Tuple[str, List[Dict]]:
        """Scrape a page and return the screenshot path if successful"""
        try:
            page = await self.start_browser()
            
            logger.info(f"Navigating to {url}")
            await page.goto(url)
            
            # Initial wait and human-like behavior
            await page.wait_for_timeout(5000)
            await self.add_human_behavior(page)
            
            # Handle cookie consent only on first visit
            if self.first_visit:
                await self.handle_cookie_consent(page)
                self.first_visit = False
            
            if "booking.com" in page.url:
                hotels = await page.locator("//div[@data-testid='property-card']").all()
                print(f"Found {len(hotels)} hotels")
                listings = []
                for hotel in hotels:
                    hotel_dict = {}
                    hotel_dict['timestamp'] = datetime.now().isoformat()
                    hotel_dict['url'] = url
                    hotel_dict['start_date'] = start_date
                    hotel_dict['end_date'] = end_date
                    
                    # Properly await all locator operations
                    title_element = hotel.locator("//div[@data-testid='title']")
                    price_element = hotel.locator("//span[@data-testid='price-and-discounted-price']")
                    rating_element = hotel.locator("//div[@data-testid='review-score']")
                    beds_element = hotel.locator("//div[@data-testid='recommended-units']")
                    
                    # Get text content with proper awaiting
                    hotel_dict['name'] = await title_element.inner_text() if await title_element.count() > 0 else "N/A"
                    price_text = await price_element.inner_text() if await price_element.count() > 0 else "N/A"
                    hotel_dict['price'] = price_text.replace(u'\xa0', u'') if price_text != "N/A" else "N/A"
                    
                    rating_text = await rating_element.inner_text() if await rating_element.count() > 0 else "N/A"
                    hotel_dict['rating'] = rating_text.split('\n')[1].strip() if rating_text != "N/A" else "N/A"
                    
                    hotel_dict['bed_configuration'] = await beds_element.inner_text() if await beds_element.count() > 0 else "N/A"
                    
                    print(hotel_dict)
                    listings.append(hotel_dict)
                return "booking", listings
            elif "airbnb.com" in page.url:
                screenshot_path = await self.get_screenshot(page, "#site-content")
                if screenshot_path:
                    # Parse the screenshot using Vision AI
                    parsed_listings = parse_listing_screenshot(screenshot_path)
                    if parsed_listings:
                        listings = []
                        for listing in parsed_listings:
                            listings.append({
                                'timestamp': datetime.now().isoformat(),
                                'url': url,
                                'start_date': start_date,
                                'end_date': end_date,
                                'listing': listing.model_dump()
                            })
                        logger.info(f"Successfully parsed {len(parsed_listings)} listings")
                        return "airbnb", listings
                return "airbnb", []
            
            return "none", []
            
        except Exception as e:
            logger.error(f"Error scraping page: {str(e)}")
            return "none", []