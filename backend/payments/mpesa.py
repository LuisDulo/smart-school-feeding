import requests
import base64
import datetime
import os
from dotenv import load_dotenv

load_dotenv()


class MPesaService:
    BASE_URL = "https://sandbox.safaricom.co.ke"

    def __init__(self):
        self.consumer_key = os.getenv('DARAJA_CONSUMER_KEY')
        self.consumer_secret = os.getenv('DARAJA_CONSUMER_SECRET')
        self.shortcode = os.getenv('DARAJA_SHORTCODE')
        self.passkey = os.getenv('DARAJA_PASSKEY')
        self.callback_url = os.getenv('DARAJA_CALLBACK_URL')

    def get_access_token(self):
        """Get OAuth2 bearer token from Daraja."""
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode('utf-8')
        ).decode('utf-8')

        response = requests.get(
            f"{self.BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()['access_token']

    def get_password(self):
        """Generate the base64 encoded password for STK Push."""
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(raw.encode('utf-8')).decode('utf-8')
        return password, timestamp

    def stk_push(self, phone_number, amount_cents, account_reference, description):
        """
        Initiate an STK Push payment request.
        phone_number: format 2547XXXXXXXX
        amount_cents: integer cents (e.g. 50000 = KES 500)
        Returns the full Daraja response dict.
        """
        token = self.get_access_token()
        password, timestamp = self.get_password()
        amount_ksh = max(1, amount_cents // 100)  # Daraja requires whole KES

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount_ksh,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": description
        }

        response = requests.post(
            f"{self.BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def query_stk_status(self, checkout_request_id):
        """Query the status of an STK Push transaction."""
        token = self.get_access_token()
        password, timestamp = self.get_password()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        response = requests.post(
            f"{self.BASE_URL}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
