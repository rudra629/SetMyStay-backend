"""
Sends email through Brevo's HTTPS API (port 443).
Render's free plan blocks normal SMTP ports, so SMTP would silently fail there.

Environment variables (set on Render):
  BREVO_API_KEY       - from Brevo > SMTP & API > API Keys
  BREVO_SENDER_EMAIL  - a sender email you verified in Brevo (Senders, Domains & Dedicated IPs)
  BREVO_SENDER_NAME   - optional, defaults to "SetMyStay"
"""
import os

import requests

BREVO_URL = 'https://api.brevo.com/v3/smtp/email'


class EmailNotConfigured(Exception):
    pass


class EmailSendFailed(Exception):
    pass


def email_is_configured():
    return bool(os.environ.get('BREVO_API_KEY') and os.environ.get('BREVO_SENDER_EMAIL'))


def send_email(to_email, subject, html, text=None):
    api_key = os.environ.get('BREVO_API_KEY')
    sender_email = os.environ.get('BREVO_SENDER_EMAIL')
    if not (api_key and sender_email):
        raise EmailNotConfigured('BREVO_API_KEY / BREVO_SENDER_EMAIL are not set')
    payload = {
        'sender': {'email': sender_email, 'name': os.environ.get('BREVO_SENDER_NAME', 'SetMyStay')},
        'to': [{'email': to_email}],
        'subject': subject,
        'htmlContent': html,
    }
    if text:
        payload['textContent'] = text
    try:
        resp = requests.post(
            BREVO_URL,
            json=payload,
            headers={'api-key': api_key, 'accept': 'application/json', 'content-type': 'application/json'},
            timeout=15,
        )
    except requests.RequestException as e:
        raise EmailSendFailed(f'Could not reach Brevo: {e}')
    if resp.status_code >= 300:
        # Do not include the API key; Brevo's error body explains what is wrong (e.g. unverified sender)
        raise EmailSendFailed(f'Brevo returned {resp.status_code}: {resp.text[:300]}')
    return True
