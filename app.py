import os
import base64
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")  # Needed for session

def get_access_token():
    """pass"""
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    auth = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]

def initiate_payment(phone_no, amount):
    """pass"""
    access_token = get_access_token()
    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")
    callback_url = os.getenv("CALLBACK_URL")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": f"254{phone_no[-9:]}",  # Ensure phone is in 2547XXXXXXXX format
        "PartyB": shortcode,
        "PhoneNumber": f"254{phone_no[-9:]}",
        "CallBackURL": callback_url,
        "AccountReference": "zeeno WiFi Payment",
        "TransactionDesc": "Payment for WiFi service"
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return response.json()

@app.route('/', methods=["GET"])
def home():
    """pass"""
    message = "mpesa_message"
    status = "mpesa_status"
    return render_template('index.html', message=message, status=status)

@app.route('/api/pay', methods=["POST"])
def pay():
    """pass"""
    phone_no = request.form.get('phone_no')
    amount = request.form.get('amount')
    resp = initiate_payment(phone_no, amount)
    print(resp)  # For debugging purposes
    # Save the CheckoutRequestID in session if you want to track it
    mpesa_message = "Payment initiated. Check your phone."
    mpesa_status = "pending"
    return redirect(url_for("afterpay"), message=mpesa_message, status=mpesa_status)

@app.route('/afterpay')
def afterpay():
    """pass"""
    message = "Waiting for payment confirmation..."
    status = "pending"
    return render_template('afterpay.html', message=message, status=status)

@app.route('/callback', methods=["GET", "POST", "PUT", "DELETE"])
def callback():
    """pass"""
    data = request.get_json()
    print(data)  # For debugging purposes
    try:
        result_code = data["Body"]["stkCallback"]["ResultCode"]
        result_desc = data["Body"]["stkCallback"]["ResultDesc"]
        if result_code == 0:
            mpesa_message = "Payment successful!"
            mpesa_status = "success"
        else:
            mpesa_message = f"Payment failed: {result_desc}"
            mpesa_status = "failed"
    except (KeyError, TypeError, ValueError):
        mpesa_message = "Error processing payment callback."
        mpesa_status = "failed"
    return redirect(url_for("afterpay", message=mpesa_message, status=mpesa_status))


if __name__ == '__main__':
    app.run(debug=True)