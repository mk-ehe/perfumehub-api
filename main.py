from fastapi import FastAPI, HTTPException
from scraper import PerfumehubScraper   
from dotenv import load_dotenv
import re
from pymongo import MongoClient
import os
from urllib.parse import urlparse
from pydantic import BaseModel


load_dotenv()

app = FastAPI()
scraper = PerfumehubScraper()

client = MongoClient(os.getenv("MONGO_URL"))
db = client.get_default_database()
collection = db["prices"]


def validate_perfumehub_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise HTTPException(status_code=400, detail="Invalid protocol.")

        domain_pattern = r"^(www\.)?perfumehub\.pl$"
        if not re.match(domain_pattern, parsed_url.netloc):
            raise HTTPException(status_code=400, detail="Invalid domain. Only official Perfumehub URLs are allowed.")

        return url
    except HTTPException:
        raise
    except Exception as e:
        print(f"URL Validation Error: {e}", flush=True)
        raise HTTPException(status_code=400, detail="Malformed URL provided.")


@app.get("/")
def guide():
    return {
        "routes": [
            "/docs",
            "[GET] /search_price?url={full_url}",
            "[GET] /subscribe?url={full_url}&email={your_email}",
            "[POST] /unsubscribe (requires JSON body: {'url': '{full_url}', 'email': '{your_email}'})"
        ],
        "author": "mk-ehe",
        "github": "https://github.com/mk-ehe/perfumehub_api"
        }

@app.get("/search")
def get_price(url: str):
    url = validate_perfumehub_url(url)
    
    try:
        scraped_data = scraper.get_data(url)
        
        db_document = {
            "fragrance": scraped_data.get("fragrance"),
            "concentration": scraped_data.get("concentration"),
            "price": scraped_data.get("price"),
            "low_30d": scraped_data.get("low_30d"),
            "shop": scraped_data.get("shop"),
            "url": url,
        }

        collection.update_one(
            {"url": url},
            {"$set": db_document},
            upsert=True
        )
        return scraped_data
    except Exception as e:
        print(f"ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching the price.")

@app.get("/subscribe")
def subscribe_price(url: str, email: str):
    url = validate_perfumehub_url(url)

    if not "@" in email:
        raise HTTPException(status_code=400, detail="Wrong email provided.")
    
    product_exists = collection.find_one({"url": url})
    
    if not product_exists:  
        try:
            scraped_data = scraper.get_data(url)
            
            db_document = {
                "fragrance": scraped_data.get("fragrance"),
                "concentration": scraped_data.get("concentration"),
                "price": scraped_data.get("price"),
                "low_30d": scraped_data.get("low_30d"),
                "shop": scraped_data.get("shop"),
                "url": url,
                "subscribers": []
            }
            collection.insert_one(db_document)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            raise HTTPException(status_code=400, detail="An error occurred while fetching the price.")

    collection.update_one(
        {"url": url},
        {"$addToSet": {"subscribers": email.lower()}}
    )

    return {"message": f"We will send price alerts to: {email}"}

class UnsubscribeRequest(BaseModel):
    url: str
    email: str

@app.post("/unsubscribe")
def unsubscribe_price(data: UnsubscribeRequest):
    valid_url = validate_perfumehub_url(data.url)
    
    result = collection.update_one(
        {"url": valid_url},
        {"$pull": {"subscribers": data.email.lower()}}
    )

    if result.modified_count == 0:
        return {"message": "You were not subscribed to this fragrance."}

    return {"message": f"Success! {data.email} has been unsubscribed from alerts for this product."}