from typing import List, Dict

def calculate_airbnb_price_analyses(listings: List[Dict]) -> Dict:
    """Calculate price statistics from a list of MongoDB listings
    
    Args:
        listings (List[Dict]): List of listings from MongoDB, where each listing has
                             a nested 'listing' object containing the price
    
    Returns:
        Dict: Dictionary containing average, highest, and lowest prices
    """
    if not listings:
        return {
            'average_price': 0,
            'highest_price': 0,
            'lowest_price': 0,
            'total_listings': 0,
            'listings_with_price': 0
        }
    
    # Filter out listings with price 0
    prices = [listing['listing']['price'] for listing in listings if listing['listing']['price'] > 0]
    
    if not prices:
        return {
            'average_price': 0,
            'highest_price': 0,
            'lowest_price': 0,
            'total_listings': len(listings),
            'listings_with_price': 0
        }
    
    return {
        'average_price': round(sum(prices) / len(prices), 2),
        'highest_price': max(prices),
        'lowest_price': min(prices),
        'total_listings': len(listings),
        'listings_with_price': len(prices)
    }

def get_airbnb_listings_summary(listings: List[Dict]) -> Dict:
    """Get a summary of the listings including price analysis and general stats
    
    Args:
        listings (List[Dict]): List of listings from MongoDB
        
    Returns:
        Dict: Summary statistics about the listings
    """
    if not listings:
        return {"message": "No listings found"}
    
    price_analysis = calculate_price_analyses(listings)
    
    # Get unique property names
    unique_properties = set(listing['listing']['name'] for listing in listings)
    
    # Get average rating
    ratings = [listing['listing']['rating'] for listing in listings if listing['listing'].get('rating')]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0
    
    return {
        'price_analysis': price_analysis,
        'unique_properties': len(unique_properties),
        'average_rating': avg_rating,
        'date_range': {
            'earliest': min(listing['start_date'] for listing in listings),
            'latest': max(listing['end_date'] for listing in listings)
        }
    }
