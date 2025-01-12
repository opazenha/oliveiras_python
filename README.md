# Oliveira's Assistant

A web scraping project for collecting and analyzing rental property data from various sources including Airbnb and Booking.com.

## Project Structure

```
oliveiras_assistant/
├── src/                    # Source code
│   ├── scrapers/          # Scraping modules for different platforms
│   ├── database/          # Database interaction modules
│   ├── parsers/           # Data parsing modules
│   └── utils/             # Utility functions and helpers
├── data/                  # Data storage
│   ├── json_listings/     # JSON data storage
│   └── screenshots/       # Screenshot storage
├── .env                   # Environment variables
└── requirements.txt       # Project dependencies
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
- MONGODB_PASSWORD
- GEMINI_API_KEY

## Usage

Run the main script:
```bash
python src/main.py
```
