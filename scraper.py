import requests
from lxml import html
import base64
import json


class PerfumehubScraper:
    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",    
            "Referer": "https://www.google.com/"
        })

        self.timeout = 10

    def fetch_page(self, url):
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status() 
            return html.fromstring(response.content)
            
        except requests.exceptions.Timeout:
            raise ConnectionError("PerfumeHub connection timed out.")
        except requests.exceptions.RequestException as e:
            print(f"ERROR: {e}", flush=True)
            raise ConnectionError(f"PerfumeHub network error: {str(e)}")
    
    def get_first_or_none(self, tree, xpath_query):
        result = tree.xpath(xpath_query)
        return result[0].strip() if result else None

    def decode_perfumehub_link(self, raw_url):
        if not raw_url or not raw_url.startswith("/click?t="):
            return raw_url
            
        try:
            token = raw_url.split("?t=")[1]

            base64_payload = token.split(".")[0]
            
            padding_needed = len(base64_payload) % 4
            if padding_needed:
                base64_payload += '=' * (4 - padding_needed)
                
            decoded_bytes = base64.urlsafe_b64decode(base64_payload)
            decoded_data = json.loads(decoded_bytes)
            
            clean_url = decoded_data.get("url")
            
            return clean_url if clean_url else "https://perfumehub.pl" + raw_url
            
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            return "https://perfumehub.pl" + raw_url


    def get_data(self, url):
        tree = self.fetch_page(url)

        brand = self.get_first_or_none(tree, '//*[@id="product-description"]/div[2]/h1/a/text()') or ""
        name = self.get_first_or_none(tree, '//*[@id="product-description"]/div[2]/h1/span/text()') or ""
        fragrance = f"{brand} {name}".strip()
        concetration = self.get_first_or_none(tree, '//*[@id="product-description"]/div[2]/h2/text()')
        price = self.get_first_or_none(tree, '//*[@id="offers-body"]/div[1]/div[3]/a/span[1]/text()')
        low_30d = self.get_first_or_none(tree, '//*[@id="offers-header"]/div[2]/div[1]/span/span/span[4]/text()')
        shop_name = self.get_first_or_none(tree, '//*[@id="offers-body"]/div[1]/div[1]/a/text()')
        raw_shop_url = self.get_first_or_none(tree, '//*[@id="offers-body"]/div[1]/div[1]/a/@href')

        data = {
            "fragrance": fragrance,
            "concentration": concetration,
            "price": price,
            "low_30d": f"{low_30d} zł" if low_30d else None,
            "shop": {
                "name": shop_name,
                "shop_url": self.decode_perfumehub_link(raw_shop_url)
            },
            "url": url
        }    

        return data
    