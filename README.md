# 🧴 Perfumehub API

A high-performance price tracking and notification engine for fragrances, built with **FastAPI** and **MongoDB**. This API powers the price-monitoring logic, manages subscribers, and handles automated email alerts.

---

## 🚀 Key Features

* **Intelligent Scraping**: Real-time extraction of fragrance data, current prices, and lowest 30-day history from Perfumehub.pl.
* **Advanced Link Decoding**: Implements a custom Base64/JSON decoder to bypass hidden shop tokens and provide direct vendor URLs.
* **Smart Subscription Logic**: Multi-user subscription management per product using MongoDB's atomic operators (`$addToSet`, `$pull`).
* **Automated Price Alerts**: Well crafted HTML email notifications triggered by a configurable price-drop threshold (5PLN & 7.5%).
* **Security First**: A token-protected `/cron-check` endpoint designed for secure, scheduled automation via external cron services.

---

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **Framework** | FastAPI |
| **Database** | MongoDB Atlas |
| **Deployment** | Render.com |
| **Mailing** | Gmail API |

---

## 📡 API Endpoints

### 1. Price Search & Cache
`GET /search?url={full_url}`
Fetches current fragrance data and synchronizes it with the MongoDB database.

### 2. Subscribe to Alerts
`GET /subscribe?url={full_url}&email={your_email}&token={token}`
Registers an email address for price-drop notifications on a specific product.

### 3. Unsubscribe
`POST /unsubscribe`
Removes a user from the alert list. Requires a JSON body: `{"url": "...", "email": "...", "token": "..."}`.

### 4. Cron Price Check
`GET /cron-check?token={your_secret_token}`
The automated heart of the API. Compares live prices with the database and dispatches emails if a promotion is detected.

### 5. Health Check
`GET /ping`
Keep-alive endpoint to prevent server sleep and monitor uptime.

---

## 📖 Usage Examples

### Search Request
**GET** `/search?url=https://perfumehub.pl/dior-sauvage-woda-toaletowa-dla-mezczyzn-100-ml`

**Response:**
```json
{
  "fragrance": "Dior Sauvage",
  "concentration": "woda toaletowa dla mężczyzn",
  "picture": "https://www.elnino-parfum.pl/data/cache/thumb_min500_max750-min500_max750-12/products/39443/1660141574/christian-dior-sauvage-woda-toaletowa-dla-mezczyzn-100-ml-425724.jpg",
  "price": "385.00 zł",
  "low_30d": "384.41 zł",
  "shop": {
    "name": "elnino-parfum.pl",
    "shop_url": "https://www.elnino-parfum.pl/dior-sauvage-woda-toaletowa-dla-mezczyzn-100-ml/"
  },
  "url": "https://perfumehub.pl/dior-sauvage-woda-toaletowa-dla-mezczyzn-100-ml"
}
