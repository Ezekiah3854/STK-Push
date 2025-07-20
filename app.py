import os
from datetime import datetime
import base64
from flask import Flask, render_template, request, redirect, url_for
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    """pass"""
    alert_visible = request.args.get("alertVisible") == "true"
    confirmation = request.args.get("message", "")
    initiated_success = request.args.get("initiatedSuccess")
    payed_success = request.args.get("payedSuccess")
    return render_template(
        "index.html",
        alertVisible=alert_visible,
        confirmation=confirmation,
        initiatedSuccess=initiated_success,
        payedSuccess=payed_success
    )

def get_access_token():
    """pass"""
    auth = f"{os.getenv('MPESA_CONSUMER_KEY')}:{os.getenv('MPESA_CONSUMER_SECRET')}"
    auth_bytes = base64.b64encode(auth.encode()).decode()
    headers = {"Authorization": f"Basic {auth_bytes}"}
    response = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        headers=headers,
        timeout=10
    )
    response.raise_for_status()
    return response.json()["access_token"]

@app.route("/api/pay", methods=["POST"])
def pay():
    """pass"""
    phone_no = request.form["phone"][1:]
    amount = request.form["amount"]
    phone = f"254{phone_no}"
    access_token = get_access_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{os.getenv('MPESA_SHORTCODE')}{os.getenv('MPESA_PASSKEY')}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    account_reference = "BeamerWiFi"

    request_data = {
        "BusinessShortCode": os.getenv("MPESA_SHORTCODE"),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": os.getenv("MPESA_SHORTCODE"),
        "PhoneNumber": phone,
        "CallBackURL": os.getenv("CALLBACK_URL"),
        "AccountReference": account_reference,
        "TransactionDesc": "Payment for Order",
    }

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=request_data,
            headers=headers,
            timeout=10
        )
        return redirect(url_for(
            "index",
            alertVisible="true",
            message="Payment initiated, check your phone to complete.",
            initiatedSuccess="done"
        ))
    except requests.exceptions.RequestException as error:
        print("Error in STK Push:", error)
        return redirect(url_for(
            "index",
            alertVisible="true",
            message="Error initiating payment. Please try again.",
            initiatedSuccess="failed"
        ))

@app.route("/callBack", methods=["POST"])
def callback():
    """pass"""
    callback_data = request.get_json()
    try:
        if callback_data["Body"]["stkCallback"]["ResultCode"] == 0:
            print("Payment successful!")
            return redirect(url_for(
                "index",
                alertVisible="true",
                message="Payment successful!",
                payedSuccess="done"
            ))
        else:
            print("Payment failed:", callback_data["Body"]["stkCallback"]["ResultDesc"])
            return redirect(url_for(
                "index",
                alertVisible="true",
                message="Payment unsuccessful. Please try again.",
                payedSuccess="failed"
            ))
    except (KeyError, TypeError) as e:
        print("Callback error:", e)
    return "Callback received", 200

if __name__ == "__main__":
    app.run(port=3400, debug=True)