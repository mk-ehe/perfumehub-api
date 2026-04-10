from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from scraper import PerfumehubScraper   
from dotenv import load_dotenv
import re
from pymongo import MongoClient
import os
from urllib.parse import urlparse
from pydantic import BaseModel, EmailStr
from email_sender import send_price_alert, verify_unsubscribe_token, generate_auth_token, verify_auth_token, send_auth_email
import secrets  
from fastapi.middleware.cors import CORSMiddleware
from time import sleep
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


load_dotenv()

app = FastAPI()

origins = [
    "https://scentwatch.vercel.app",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
            "[GET] /docs",
            "[GET] /search?url={full_url}",
            "[GET] /subscribe?url={full_url}&email={your_email}&token={token},
            "[GET] /cron-check?token={your_custom_token}",
            "[GET] /ping",
            "[POST] /unsubscribe (requires JSON body: {'url': '{full_url}', 'email': '{your_email}', 'token': {token}})"
        ],
        "author": "mk-ehe",
        "github": "https://github.com/mk-ehe/perfumehub_api"
        }

@app.get("/search")
@limiter.limit("1/second, 15/minute")
def get_price(request: Request, url: str):
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
            "picture": scraped_data.get("picture"),
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
        print(f"ERROR: {str(e)}, route: /search", flush=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching the price.")

@app.get("/subscribe")
@limiter.limit("1/second, 5/minute, 20/hour")
def subscribe_price(request: Request, url: str, email: EmailStr, token: str):
    url = validate_perfumehub_url(url)
    email_lower = email.lower()

    if not verify_auth_token(email_lower, token):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    product_exists = collection.find_one({"url": url})

    if product_exists:
        if email_lower in product_exists.get("subscribers", []):
            return {"message": "You are already subscribed to this fragrance."}
        
        collection.update_one({"url": url}, {"$addToSet": {"subscribers": email_lower}})
        print(f"INFO: {email_lower} subscribed to: {product_exists.get("fragrance")}!", flush=True)
        return {"message": "Fragrance successfully added to your alerts!"}

    try:
        scraped_data = scraper.get_data(url)
        db_document = {
            "fragrance": scraped_data.get("fragrance"),
            "concentration": scraped_data.get("concentration"),
            "picture": scraped_data.get("picture"),
            "price": scraped_data.get("price"),
            "low_30d": scraped_data.get("low_30d"),
            "shop": scraped_data.get("shop"),
            "url": url,
            "subscribers": [email_lower]
        }
        collection.insert_one(db_document)
        print(f"INFO: {email_lower} subscribed to: {db_document["fragrance"]}!", flush=True)
        return {"message": "Fragrance successfully added to your alerts!"}
    except Exception as e:
        print(f"ERROR: {e}, route: /subscribe", flush=True)
        raise HTTPException(status_code=400, detail="Error while fetching data.")

class UnsubscribeRequest(BaseModel):
    url: str
    email: EmailStr
    token: str

@app.post("/unsubscribe")
@limiter.limit("20/hour")
def unsubscribe_price(request: Request, data: UnsubscribeRequest):
    valid_url = validate_perfumehub_url(data.url)

    is_valid_unsub = verify_unsubscribe_token(data.email.lower(), valid_url, data.token)
    is_valid_auth = verify_auth_token(data.email.lower(), data.token)

    if not (is_valid_unsub or is_valid_auth):
        raise HTTPException(status_code=403, detail="Unauthorized.")
    
    result = collection.update_one(
        {"url": valid_url},
        {"$pull": {"subscribers": data.email.lower()}}
    )

    if result.modified_count == 0:
        return {"message": "You were not subscribed to this fragrance."}

    return {"message": f"Success! {data.email} has been unsubscribed from alerts for this product."}

class AuthRequest(BaseModel):
    email: EmailStr

@app.post("/request-access")
@limiter.limit("1/minute, 5/hour")
def request_access(request: Request, data: AuthRequest, background_tasks: BackgroundTasks):
    email_lower = data.email.lower()
    token = generate_auth_token(email_lower)
    background_tasks.add_task(send_auth_email, email_lower, token)
    print(f"Access link has been sent to {email_lower}.", flush=True)
    return {"message": "Access link has been sent to your e-mail."}

@app.get("/my-alerts")
@limiter.limit("30/minute")
def get_my_alerts(request: Request, email: str, token: str):
    email_lower = email.lower()
    if not verify_auth_token(email_lower, token):
        raise HTTPException(status_code=403, detail="Unauthorized.")
    
    user_perfumes = list(collection.find(
        {"subscribers": email_lower},
        {"_id": 0, "fragrance": 1, "picture": 1, "price": 1, "low_30d": 1, "url": 1}
    ).sort("fragrance", 1))
    return {"alerts": user_perfumes}

def parse_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    clean_str = price_str.replace("zł", "").replace(" ", "").replace(",", ".")
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def process_all_prices():
    products = collection.find({})
    
    for product in products:
        url = product.get("url")
        subscribers = product.get("subscribers", [])
        
        if not subscribers:
            continue
            
        old_price_str = product.get("price")
        fragrance_name = product.get("fragrance", "Ulubiony zapach")
        picture = product.get("picture")
        is_good_deal = False

        try:
            scraped_data = scraper.get_data(url)
            new_price_str = scraped_data.get("price")

            low_30d = scraped_data.get("low_30d") or "Brak"

            shop_data = scraped_data.get("shop", {})

            shop_url = shop_data.get("shop_url") or url
            if not shop_url.startswith(("http://", "https://")):
                shop_url = url
                shop_data["shop_url"] = shop_url
            
            if not new_price_str or not old_price_str:
                continue
            
            old_p = parse_price(old_price_str)
            new_p = parse_price(new_price_str)
            
            if old_p <= 0: continue

            price_diff = round(old_p - new_p, 2)
            formatted_diff = f"{price_diff:.2f} zł".replace(".", ",")

            percentage = 7 <= (1 - new_p / old_p) * 100
            is_good_deal = price_diff >= 5.00 and percentage
            price_went_up = new_p > old_p
            
            set_fields = {
                "low_30d": low_30d,
                "shop": shop_data
            }

            new_picture = scraped_data.get("picture")
            if new_picture:
                set_fields["picture"] = new_picture
                picture = new_picture

            if is_good_deal or price_went_up:
                set_fields["price"] = new_price_str

            update_doc = {"$set": set_fields}

            if is_good_deal:
                print(f"INFO: Threshold REACHED! {fragrance_name}: Price difference: {price_diff}zł, new price: {new_p}zł, old price: {old_p}zł.", flush=True)
                for email in subscribers:
                    send_price_alert(
                        to_email=email,
                        fragrance_name=fragrance_name,
                        picture=picture,
                        old_price=old_price_str,
                        new_price=new_price_str,
                        price_diff=formatted_diff,
                        low_30d=low_30d,
                        product_url=url,
                        shop_url=shop_url
                    )
                    sleep(1)
                
                update_doc["$inc"] = {"emails_sent": len(subscribers)}
            else:
                if new_p == old_p:
                    print(f"INFO: Threshold NOT reached. {fragrance_name}: Price difference: {price_diff}zł, price: {old_p}zł", flush=True)
                else:
                    print(f"INFO: Threshold NOT reached. {fragrance_name}: Price difference: {price_diff}zł, new price: {new_p}zł, old price: {old_p}zł.", flush=True)

            collection.update_one({"_id": product["_id"]}, update_doc)
            

        except Exception as e:
            error_message = str(e)
            
            if "404 Client Error" in error_message or "404" in error_message:
                print(f"INFO: {fragrance_name}: 404 not found, removing...", flush=True)
                collection.delete_one({"_id": product["_id"]})
            else:
                print(f"ERROR: Error while checking: {url}: {error_message}, route: /cron-check", flush=True)

        if not is_good_deal:
            sleep(3)

    print("INFO: Cron check completed.", flush=True)

@app.get("/cron-check")
def run_price_checks(background_tasks: BackgroundTasks, token: str = ""):
    expected_token = os.getenv("CRON_SECRET")
    if not secrets.compare_digest(token, expected_token or ""):
        raise HTTPException(status_code=401, detail="Unauthorized")

    background_tasks.add_task(process_all_prices)

    print("INFO: Cron check started.", flush=True)
    return {"message": "Cron check started."}

@app.get("/ping")
@limiter.limit("20/hour")
def ping(request: Request):
    return {"status": "ok"}
