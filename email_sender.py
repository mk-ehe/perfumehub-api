from datetime import datetime, timezone, timedelta
import os
import base64
import json
import html
from urllib.parse import quote
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import hmac
import hashlib
import secrets
import time


load_dotenv()

WINDOW_SECONDS = 1 * 3600

def get_gmail_service():
    token_data = os.getenv("GMAIL_TOKEN_JSON")
    
    if token_data:
        creds_info = json.loads(token_data)
        creds = Credentials.from_authorized_user_info(creds_info)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    else:
        raise Exception("Brak autoryzacji! Wygeneruj token.json lub ustaw zmienną GMAIL_TOKEN_JSON")

    return build('gmail', 'v1', credentials=creds)

def generate_unsubscribe_token(email: str, url: str) -> str:
    secret = os.getenv("UNSUB_SECRET").encode('utf-8')
    message = f"{email.lower()}:{url}".encode('utf-8')
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return signature

def verify_unsubscribe_token(email: str, url: str, token: str) -> bool:
    expected_token = generate_unsubscribe_token(email, url)
    return secrets.compare_digest(expected_token, token)

def send_via_api(message_object):
    service = get_gmail_service()
    encoded_message = base64.urlsafe_b64encode(message_object.as_bytes()).decode()
    create_message = {'raw': encoded_message}
    
    send_message = service.users().messages().send(userId="me", body=create_message).execute()
    return send_message

def send_price_alert(to_email: str, fragrance_name: str, picture: str, old_price: str, new_price: str, price_diff: str, low_30d: str, product_url: str, shop_url: str):
    gmail_address = os.getenv("GMAIL_ADDRESS")
    frontend_url = os.getenv("FRONTEND_URL")
    safe_name = html.escape(fragrance_name)
    safe_email = quote(to_email)
    safe_url = quote(product_url)
    token = generate_unsubscribe_token(to_email, product_url)
    unsub_link = f"{frontend_url}/wypisz?email={safe_email}&url={safe_url}&token={token}"

    image_block = ""
    if picture:
        image_block = f'<a href="{product_url}"><img src="{picture}" style="max-width: 200px; max-height: 200px; object-fit: contain; display: block; border: none;"></a>'

    msg = EmailMessage()
    msg['Subject'] = f"📉 Spadek ceny: {fragrance_name}!"
    msg['From'] = f"ScentWatch <{gmail_address}>" 
    msg['To'] = to_email

    body = f"""
<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f5f7; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f4f5f7; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e4e4e4">
                        
                        <tr>
                            <td align="center" style="background-color: #155dfc; padding: 25px 20px;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 32px; letter-spacing: 1px;">ScentWatch</h1>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="padding: 28px 28px;">
                                <h2 style="color: #333333; margin: 0; font-size: 28px;">🎉 Świetne wieści! 🎉</h2>
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin-bottom: 10px; margin-top: 22px;">
                                    Cena dla zapachu <br>
                                    <strong style="color: #1a1a1a; font-size: 18px;"><a href="{product_url}"><u>{safe_name}</u></a></strong><br>
                                    który obserwujesz, właśnie spadła o <strong style="color: #e91010; font-size: 18px;"><u>{price_diff}</u></strong>.
                                </p>
                                <b style="font-size: 22px; color: #1a1a1a; ;">Stara cena: {old_price}</b>

                                
                                <table border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 10px; margin-top: 15px; width: 80%;">
                                    <tr>
                                        <td align="center" style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 10px 20px 5px 20px;">
                                            <p style="margin: 0 0 0 0; color: #888888; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Nowa cena</p>
                                            <p style="margin: 0 0 0 0; color: #0fc74d; font-size: 44px; font-weight: bold;">{new_price}</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                {image_block}

                                <table border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td align="center" style="padding-bottom: 28px;">
                                            <p style="color: #999999; font-size: 12px; margin: 0;">
                                                Najniższa cena sprzed 30 dni: {low_30d}.</p>
                                    </tr>
                                    <tr>
                                        <td align="center" style="background-color: #155dfc; border-radius: 8px;">
                                            <a href="{shop_url}" target="_blank" style="display: inline-block; padding: 16px 35px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold; border-radius: 6px;">
                                                Zobacz ofertę
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <tr>
                            <td align="center" style="background-color: #f8f9fa; padding: 25px; border-top: 1px solid #eeeeee;">
                                <p style="color: #999999; font-size: 12px; margin: 0; line-height: 1.5;">
                                    Wiadomość wygenerowana automatycznie przez ScentWatch.<br>
                                    Jeśli nie chcesz już śledzić tego zapachu, możesz się <a href="{unsub_link}" style="color: #4b4b4b; text-decoration: underline;">wypisać z powiadomień</a>.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    msg.add_alternative(body, subtype='html')

    try:
        send_via_api(msg)
        print(f"INFO: E-mail sent successfully to {to_email} about {fragrance_name}", flush=True)
        return True
    except Exception as e:
        print(f"INFO: Error while sending e-mail to: {to_email} about {fragrance_name}: {e}", flush=True)
        return False


def generate_auth_token(email: str) -> str:
    secret = os.getenv("AUTH_SECRET").encode('utf-8')
    current_window = int(time.time() // WINDOW_SECONDS)
    message = f"auth:{email.lower()}:{current_window}".encode('utf-8')
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return signature

def verify_auth_token(email: str, token: str) -> bool:
    if secrets.compare_digest(generate_auth_token(email), token):
        return True

    secret = os.getenv("AUTH_SECRET").encode('utf-8')
    previous_window = int(time.time() // WINDOW_SECONDS) - 1
    msg_yesterday = f"auth:{email.lower()}:{previous_window}".encode('utf-8')
    sig_yesterday = hmac.new(secret, msg_yesterday, hashlib.sha256).hexdigest()
    return secrets.compare_digest(sig_yesterday, token)


def send_auth_email(to_email: str, token: str):
    sender_email = os.getenv("GMAIL_ADDRESS")
    frontend_url = os.getenv("FRONTEND_URL") 
    
    safe_email = quote(to_email)
    auth_link = f"{frontend_url}/alerty?email={safe_email}&token={token}"

    msg = EmailMessage()
    msg['Subject'] = "Twój link dostępu do panelu ScentWatch"
    msg['From'] = f"ScentWatch <{sender_email}>"
    msg['To'] = to_email

    html_content = f"""
<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f5f7; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="padding: 40px 0;">
            <tr>
                <td align="center">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e4e4e4">
                        <tr>
                            <td align="center" style="background-color: #155dfc; padding: 25px 20px;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 32px; letter-spacing: 1px;">ScentWatch</h1>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="padding: 40px 28px;">
                                <h2 style="color: #333333; margin-top: 0; font-size: 24px;">🔐 Potwierdzenie 🔐</h2>
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                                    Oto Twój ograniczony czasowo link do panelu. Kliknij poniżej, aby dodać lub usunąć swoje alerty cenowe:
                                </p>
                                <table border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 20px;">
                                    <tr>
                                        <td align="center" style="background-color: #155dfc; border-radius: 6px;">
                                            <a href="{auth_link}" target="_blank" style="display: inline-block; padding: 16px 35px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold; border-radius: 6px;">
                                                Otwórz panel ScentWatch
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="background-color: #f8f9fa; padding: 20px; border-top: 1px solid #eeeeee;">
                                <p style="color: #999999; font-size: 12px; margin: 0; line-height: 1.5;">
                                    Jeśli to nie Ty prosiłeś o dostęp, po prostu zignoruj tę wiadomość.<br>
                                    Link jest generowany automatycznie.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    msg.add_alternative(html_content, subtype='html')

    try:
        send_via_api(msg)
        print(f"INFO: Auth e-mail sent successfully to {to_email}", flush=True)
        return True
    except Exception as e:
        print(f"INFO: Error while sending auth e-mail to: {to_email}: {e}", flush=True)
        return False