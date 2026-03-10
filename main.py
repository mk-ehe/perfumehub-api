from fastapi import FastAPI, HTTPException, BackgroundTasks
from scraper import PerfumehubScraper   
from dotenv import load_dotenv
import re
from pymongo import MongoClient
import os
from urllib.parse import urlparse
from pydantic import BaseModel, EmailStr
from email_sender import send_price_alert, send_confirmation_email
import secrets
from datetime import datetime, timezone, timedelta


load_dotenv()

app = FastAPI()
scraper = PerfumehubScraper()

client = MongoClient(os.getenv("MONGO_URL"))
db = client.get_default_database()
collection = db["prices"]
pending_collection = db["pending_subscribers"]


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
            "[GET] /search?url={full_url}",
            "[GET] /subscribe?url={full_url}&email={your_email}",
            "[GET] /confirm?token={generated_token}",
            "[GET] /cron-check?token={your_custom_token}",
            "[GET] /ping",
            "[POST] /unsubscribe (requires JSON body: {'url': '{full_url}', 'email': '{your_email}'})"
        ],
        "author": "mk-ehe",
        "github": "https://github.com/mk-ehe/perfumehub_api"
        }

@app.get("/search")
def get_price(url: str):
    url = validate_perfumehub_url(url)

    existing_product = collection.find_one({"url": url})
    if existing_product:
        existing_product.pop("_id", None)
        existing_product.pop("subscribers", None)
        return existing_product
    
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
        db_document.pop("_id", None)
        db_document.pop("subscribers", None)
        return db_document

    except Exception as e:
        print(f"ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching the price.")

@app.get("/subscribe")
def subscribe_price(url: str, email: EmailStr, background_tasks: BackgroundTasks):
    url = validate_perfumehub_url(url)
    email_lower = email.lower()
    
    fragrance_name = ""
    concentration = ""

    product_exists = collection.find_one({"url": url})
    
    if product_exists and email_lower in product_exists.get("subscribers", []):
        return {"message": f"You are already subscribed to this fragrance."}
    
    pending_exists = pending_collection.find_one({"url": url, "email": email_lower})
    if pending_exists:
        return {"message": "Verification e-mail has already been sent to your Inbox!"}
    
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
            fragrance_name = scraped_data.get("fragrance")
            concentration = scraped_data.get("concentration")
            collection.insert_one(db_document)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            raise HTTPException(status_code=400, detail="An error occurred while fetching the price.")
    elif product_exists:
        fragrance_name = product_exists.get("fragrance")
        concentration = product_exists.get("concentration")

        try:
            update_data = scraper.get_data(url)
            collection.update_one(
                {"url": url},
                {"$set": {"price": update_data.get("price")}}
            )
        except Exception:
            pass

    token = secrets.token_urlsafe(16)

    pending_collection.insert_one({
        "fragrance": fragrance_name,
        "concentration": concentration,
        "email": email_lower,
        "url": url,
        "token": token,
        "created_at": datetime.now(timezone.utc)
    })  

    base_url = os.getenv("API_BASE_URL", "https://perfumehub-api.onrender.com")
    
    background_tasks.add_task(send_confirmation_email, email_lower, url, token, base_url, fragrance_name)

    return {"message": f"Verification email sent to: {email_lower}. Check your inbox!"}

@app.get("/confirm")
def confirm_subscription(token: str):
    pending_doc = pending_collection.find_one({"token": token})
    
    if not pending_doc:
        raise HTTPException(status_code=400, detail="Incorrect or expired token.")
        
    url = pending_doc["url"]
    email = pending_doc["email"]
    fragrance = pending_doc["fragrance"]

    collection.update_one(
        {"url": url},
        {"$addToSet": {"subscribers": email}}
    )

    pending_collection.delete_one({"_id": pending_doc["_id"]})

    return {"message": f"E-mail confirmed. You will receive promotion alerts on: {email.lower()} about {fragrance}."}

class UnsubscribeRequest(BaseModel):
    url: str
    email: EmailStr

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

def parse_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    clean_str = price_str.replace("zł", "").replace(" ", "").replace(",", ".")
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def process_all_prices():
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=6)
    pending_collection.delete_many({"created_at": {"$lt": cutoff_time}})

    products = collection.find({})
    
    for product in products:
        url = product.get("url")
        subscribers = product.get("subscribers", [])
        
        if not subscribers:
            continue
            
        old_price_str = product.get("price")
        fragrance_name = product.get("fragrance", "Ulubiony zapach")
        
        try:
            scraped_data = scraper.get_data(url)
            new_price_str = scraped_data.get("price")

            low_30d = scraped_data.get("low_30d") or "Brak"

            shop_data = scraped_data.get("shop", {})

            shop_url = shop_data.get("shop_url") or url
            if not shop_url.startswith(("http://", "https://")):
                shop_url = url
            
            if not new_price_str or not old_price_str:
                continue
            
            old_p = parse_price(old_price_str)
            new_p = parse_price(new_price_str)
            
            if old_p <= 0: continue

            price_diff = round(old_p - new_p, 2)
            formatted_diff = f"{price_diff:.2f} zł".replace(".", ",")

            percentage = 10 <= (1 - new_p / old_p) * 100
            is_good_deal = price_diff >= 5.00 and percentage
            price_went_up = new_p > old_p
            
            set_fields = {
                "low_30d": low_30d,
                "shop": shop_data
            }

            if is_good_deal or price_went_up:
                set_fields["price"] = new_price_str

            update_doc = {"$set": set_fields}

            if is_good_deal:  
                for email in subscribers:
                    send_price_alert(
                        to_email=email,
                        fragrance_name=fragrance_name,
                        old_price=old_price_str,
                        new_price=new_price_str,
                        price_diff=formatted_diff,
                        low_30d=low_30d,
                        product_url=url,
                        shop_url=shop_url
                    )
                
                update_doc["$inc"] = {"emails_sent": len(subscribers)}
                print(f"{fragrance_name}: Threshold reached! Price difference: {price_diff}", flush=True)
            else:
                print(f"{fragrance_name}: Threshold not exceeded. Price difference: {price_diff}", flush=True)

            collection.update_one({"_id": product["_id"]}, update_doc)
                
        except Exception as e:
            print(f"ERROR: Error while checking: {url}: {e}", flush=True)

    print("INFO: Cron check completed")

@app.get("/cron-check")
def run_price_checks(background_tasks: BackgroundTasks, token: str = ""):
    expected_token = os.getenv("CRON_SECRET")
    if not secrets.compare_digest(token, expected_token or ""):
        raise HTTPException(status_code=401, detail="Unauthorized")

    background_tasks.add_task(process_all_prices)

    print("INFO: Cron check started.")
    return {"message": "Cron check started."}

@app.get("/ping")
def ping():
    return {"status": "ok"}
