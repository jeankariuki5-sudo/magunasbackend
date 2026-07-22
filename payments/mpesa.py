import requests
import base64
from datetime import datetime
from decouple import config


CONSUMER_KEY = config('MPESA_CONSUMER_KEY')
CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET')
SHORTCODE = config('MPESA_SHORTCODE')
PASSKEY = config('MPESA_PASSKEY')
CALLBACK_URL = config('MPESA_CALLBACK_URL')

# Sandbox URLs — swap for live when deploying
OAUTH_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
STK_PUSH_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'


def GetAccessToken():
    """Get OAuth token from Daraja"""
    try:
        credentials = base64.b64encode(
            f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()
        ).decode()

        response = requests.get(
            OAUTH_URL,
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json',
            }
        )

        result = response.json()
        return result.get('access_token')

    except Exception as e:
        return None


def GeneratePassword():
    """Generate base64 password for STK push"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f"{SHORTCODE}{PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def InitiateSTKPush(phone_number, amount, order_id):
    """
    Send STK push to customer phone.
    phone_number should be in format 254XXXXXXXXX
    """
    access_token = GetAccessToken()

    if not access_token:
        return None, 'Failed to get access token from Daraja'

    password, timestamp = GeneratePassword()

    # Format phone number — remove leading 0 and add 254
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]

    payload = {
        'BusinessShortCode': SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(amount),  # M-Pesa requires integer amount
        'PartyA': phone_number,
        'PartyB': SHORTCODE,
        'PhoneNumber': phone_number,
        'CallBackURL': CALLBACK_URL,
        'AccountReference': f'Magunas Order #{order_id}',
        'TransactionDesc': f'Payment for Order #{order_id}'
    }

    try:
        response = requests.post(
            STK_PUSH_URL,
            json = payload,
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
        )

        result = response.json()
        print('STK PUSH RESPONSE:', result) #debug
        return result, None

    except Exception as e:
        print('STK PUSH ERROR:', str(e)) #debug
        return None, str(e)