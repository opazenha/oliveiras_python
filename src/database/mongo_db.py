from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from typing import List
from dotenv import load_dotenv

import os
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MongoDBClient:
    def __init__(self):
        self.db_password = os.getenv('MONGODB_PASSWORD')
        if not self.db_password:
            raise ValueError("MongoDB password not found in environment variables")
        
        self.uri = f"mongodb+srv://opazenha:{self.db_password}@opazenha.pwkyvkg.mongodb.net/?retryWrites=true&w=majority&appName=opazenha"
        self.client = MongoClient(self.uri, server_api=ServerApi('1'))
        self.db = self.client.oliveiras
        
        # Test connection
        try:
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB Atlas!")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def insert_listings(self, listings: List, collection_name: str) -> None:
        """Insert listings into MongoDB"""
        try:
            if not listings:
                logger.warning("No data to save")
                return
            
            self.collection = self.db[collection_name]

            # Convert listings to dictionaries and add timestamp
            listings_dict = []
            for listing in listings:
                # Handle both Pydantic models and regular dictionaries
                if hasattr(listing, 'model_dump'):
                    listing_dict = listing.model_dump()  # For Pydantic models
                else:
                    listing_dict = listing  # Already a dictionary
                
                listing_dict['inserted_at'] = datetime.now().isoformat()
                listings_dict.append(listing_dict)
            
            result = self.collection.insert_many(listings_dict)
            logger.info(f"Successfully inserted {len(result.inserted_ids)} listings into MongoDB")
        except Exception as e:
            logger.error(f"Failed to insert listings into MongoDB: {str(e)}")
            raise
    
    def get_airbnb_listings(self) -> List:
        """Get all airbnb listings from MongoDB"""
        try:
            return list(self.collection.find())
        except Exception as e:
            logger.error(f"Failed to get airbnb listings from MongoDB: {str(e)}")
            raise

    def get_airbnb_listings_by_date_range(self, start_date: str, end_date: str) -> List:
        """Get listings within a specific date range
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            List: List of listings within the date range
        """
        try:
            query = {
                'start_date': {'$gte': start_date},
                'end_date': {'$lte': end_date}
            }
            return list(self.collection.find(query))
        except Exception as e:
            logger.error(f"Failed to get listings by date range: {str(e)}")
            raise

    def get_airbnb_listings_by_name(self, name_pattern: str) -> List:
        """Get listings where name contains the given pattern
        
        Args:
            name_pattern (str): Pattern to search for in listing names
            
        Returns:
            List: List of listings matching the name pattern
        """
        try:
            query = {
                'listing.name': {'$regex': name_pattern, '$options': 'i'}  # case-insensitive
            }
            return list(self.collection.find(query))
        except Exception as e:
            logger.error(f"Failed to get listings by name: {str(e)}")
            raise
    
    def close(self):
        """Close the MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")