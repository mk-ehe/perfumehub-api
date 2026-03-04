from fastapi import FastAPI, HTTPException
from scraper import PerfumehubScraper   
from dotenv import load_dotenv
import re
from pymongo import MongoClient
import os
from urllib.parse import urlparse


load_dotenv()

app = FastAPI()
scraper = PerfumehubScraper()

client = MongoClient(os.getenv("MONGO_URL"))
db = client["perfumehub_db"]
collection = db["prices"]

@app.get("/")
def home():
    pass

@app.get("/search_price")
def get_price(url: str):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise HTTPException(status_code=400, detail="Invalid protocol.")

        domain_pattern = r"^(www\.)?perfumehub\.pl$"
        if not re.match(domain_pattern, parsed_url.netloc):
            raise HTTPException(status_code=400, detail="Invalid domain. Only official Perfumehub URLs are allowed.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=400, detail="Malformed URL provided.")
    
    try:
        scraped_data = scraper.get_data(url)
        
        db_document = {
            "url": url,
            "price": scraped_data.get("price"),
            "low_30d": scraped_data.get("low_30d"),
            "shop": scraped_data.get("shop")
        }

        collection.update_one(
            {"url": url},
            {"$set": db_document},
            upsert=True
        )

        return scraped_data

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"Scraping error: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching the price.")