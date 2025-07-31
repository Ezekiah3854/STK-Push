import os
import base64
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session
from flask_session import Session
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config['SESSION_PARMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

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
    return render_template('index.html')

@app.route('/api/pay', methods=["POST"])
def pay():
    """pass"""
    phone_no = request.form.get('phone_no')
    amount = request.form.get('amount')

    resp = initiate_payment(phone_no, amount)
    print(resp)

    session["mpesa_message"] = "Payment initiated. Check your phone."
    session["mpesa_status"] = "pending"
    return render_template("afterpay.html", message=session["mpesa_message"], status=session["mpesa_status"])

@app.route('/afterpay')
def afterpay():
    """pass"""
    return render_template('afterpay.html')

@app.route('/callback', methods=["POST"])
def callback():
    """pass"""
    data = request.get_json()
    print(data)
    try:
        result_code = data["Body"]["stkCallback"]["ResultCode"]
        result_desc = data["Body"]["stkCallback"]["ResultDesc"]
        if result_code == 0:
            session["mpesa_message"] = "Payment successful!"
            session["mpesa_status"] = "success"
        else:
            session["mpesa_message"] = f"Payment failed: {result_desc}"
            session["mpesa_status"] = "failed"
    except (KeyError, TypeError, ValueError):
        session["mpesa_message"] = "Error processing payment callback."
        session["mpesa_status"] = "failed"
    return "OK", 200

@app.route('/payment_status')
def payment_status():
    """pass"""
    status = session.get("mpesa_status")
    message = session.get("mpesa_message")
    return {"status": status, "message": message}

if __name__ == '__main__':
    app.run(debug=True)