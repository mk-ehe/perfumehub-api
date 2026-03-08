import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import html
from urllib.parse import quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import socket

orig_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4(*args, **kwargs):
    responses = orig_getaddrinfo(*args, **kwargs)
    return [res for res in responses if res[0] == socket.AF_INET]

socket.getaddrinfo = getaddrinfo_ipv4

load_dotenv()

def send_price_alert(to_email: str, fragrance_name: str, old_price: str, new_price: str, price_diff: str, product_url: str, shop_url: str):
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    frontend_url = os.getenv("FRONTEND_URL", "#")
    safe_name = html.escape(fragrance_name)
    safe_email = quote(to_email)
    safe_url = quote(product_url)
    unsub_link = f"{frontend_url}/unsubscribe?email={safe_email}&url={safe_url}"

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
                            <td align="center" style="background-color: #0084ff; padding: 25px 20px;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 32px; letter-spacing: 1px;">ScentWatch</h1>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="padding: 40px 30px;">
                                <h2 style="color: #333333; margin-top: 0; font-size: 24px;">🎉 Świetne wieści! 🎉</h2>
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin-bottom: 24px; margin-top: 22px;">
                                    Cena dla zapachu <br>
                                    <strong style="color: #1a1a1a; font-size: 18px;"><a href="{product_url}"><u>{safe_name}</u></a></strong><br>
                                    który obserwujesz, właśnie spadła o <strong style="color: #e91010; font-size: 18px;"><u>{price_diff}</u></strong>.
                                    <br>
                                    <b style="font-size: 22px; color: #1a1a1a;">Stara cena: {old_price}</b>
                                </p>
                                <table border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 30px; width: 80%;">
                                    <tr>
                                        <td align="center" style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px 25px 25px 25px;">
                                            <p style="margin: 10px 0 0 0; color: #888888; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Nowa cena</p>
                                            <p style="margin: 5px 0 0 0; color: #0fc74d; font-size: 44px; font-weight: bold;">{new_price}</p>
                                        </td>
                                    </tr>
                                </table>

                                <table border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td align="center" style="background-color: #0084ff; border-radius: 6px;">
                                            <a href="{shop_url}" target="_blank" style="display: inline-block; padding: 16px 35px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold; border-radius: 6px;">
                                                Zobacz ofertę
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="background-color: #f8f9fa; padding: 20px; border-top: 1px solid #eeeeee;">
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
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_address, gmail_password)
            smtp.send_message(msg)
        print(f"E-mail sent successfully to {to_email}", flush=True)
        return True
    except Exception as e:
        print(f"Error while sending e-mail to: {to_email}: {e}", flush=True)
        return False

def send_confirmation_email(to_email: str, product_url: str, token: str, base_url: str, fragrance_name: str):
    sender_email = os.getenv("GMAIL_ADDRESS")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    safe_name = html.escape(fragrance_name)
    safe_url = quote(product_url)
    confirm_link = f"{base_url}/confirm?token={token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Potwierdź subskrypcję - ScentWatch"
    message["From"] = f"ScentWatch <{sender_email}>" 
    message["To"] = to_email

    html_content = f"""
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
                            <td align="center" style="background-color: #0084ff; padding: 25px 20px;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 32px; letter-spacing: 1px;">ScentWatch</h1>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="padding: 40px 30px;">
                                <h2 style="color: #333333; margin-top: 0; font-size: 24px;">📩 Prawie gotowe! 📩</h2>
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin-bottom: 22px; margin-top: 22px;">
                                    Ktoś (mamy nadzieję, że Ty) poprosił o powiadomienia o spadku ceny dla zapachu: <br>
                                    <strong style="color: #1a1a1a; font-size: 18px;"><a href="{safe_url}"><u>{safe_name}</u></a></strong>
                                </p>

                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                                    Aby potwierdzić swój adres e-mail i zacząć oszczędzać, kliknij w poniższy przycisk:
                                </p>

                                <table border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 10px;">
                                    <tr>
                                        <td align="center" style="background-color: #0fc74d; border-radius: 6px;">
                                            <a href="{confirm_link}" target="_blank" style="display: inline-block; padding: 16px 35px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold; border-radius: 6px;">
                                                Potwierdzam subskrypcję
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="background-color: #f8f9fa; padding: 20px; border-top: 1px solid #eeeeee;">
                                <p style="color: #999999; font-size: 12px; margin: 0; line-height: 1.5;">
                                    Jeśli to nie Ty prosiłeś o powiadomienia, zignoruj tę wiadomość.<br>
                                    Wiadomość wygenerowana automatycznie przez ScentWatch.
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
    
    message.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, to_email, message.as_string())
            
        print(f"E-mail sent successfully to {to_email}", flush=True)
    except Exception as e:
        print(f"Error while sending e-mail to: {to_email}: {e}", flush=True)