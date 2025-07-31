import os
import base64
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")  # Needed for session

def get_access_token():
    """Get M-Pesa access token"""
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    auth = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]

def initiate_payment(phone_no, amount):
    """Initiate M-Pesa STK Push payment"""
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
    """Home page"""
    # Get messages from session and clear them after displaying
    message = session.pop("mpesa_message", None)
    status = session.pop("mpesa_status", None)
    return render_template('index.html', message=message, status=status)

@app.route('/api/pay', methods=["POST"])
def pay():
    """Process payment request"""
    phone_no = request.form.get('phone_no')
    amount = request.form.get('amount')
    
    # Validate input
    if not phone_no or not amount:
        session["mpesa_message"] = "Phone number and amount are required"
        session["mpesa_status"] = "error"
        return redirect(url_for("home"))
    
    try:
        resp = initiate_payment(phone_no, amount)
        print(f"M-Pesa Response: {resp}")  # For debugging
        
        # Check if the request was successful
        if resp.get("ResponseCode") == "0":
            # Store the checkout request ID for tracking
            session["checkout_request_id"] = resp.get("CheckoutRequestID")
            session["mpesa_message"] = resp.get("CustomerMessage", "Payment initiated. Check your phone.")
            session["mpesa_status"] = "pending"
        else:
            # Handle M-Pesa API errors
            error_message = resp.get("errorMessage", "Payment initiation failed")
            session["mpesa_message"] = f"Error: {error_message}"
            session["mpesa_status"] = "failed"
            
    except Exception as e:
        print(f"Payment initiation error: {e}")
        session["mpesa_message"] = "Payment initiation failed. Please try again."
        session["mpesa_status"] = "failed"
    
    return redirect(url_for("afterpay"))

@app.route('/afterpay')
def afterpay():
    """Payment status page"""
    message = session.get("mpesa_message", "Processing payment...")
    status = session.get("mpesa_status", "pending")
    return render_template('afterpay.html', message=message, status=status)

@app.route('/callback', methods=["POST"])  # M-Pesa sends POST requests
def callback():
    """Handle M-Pesa payment callback"""
    print("Callback endpoint hit!")
    
    # Get the JSON data from the request
    data = request.get_json()
    print(f"Callback data received: {data}")
    
    # Handle case where no JSON data is received
    if not data:
        print("No JSON data received in callback")
        return "No data received", 400
    
    try:
        # Extract callback information
        stk_callback = data["Body"]["stkCallback"]
        result_code = stk_callback["ResultCode"]
        result_desc = stk_callback["ResultDesc"]
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        print(f"Payment result: Code={result_code}, Description={result_desc}")
        
        if result_code == 0:
            # Payment successful - extract transaction details
            callback_metadata = stk_callback.get("CallbackMetadata", {})
            items = callback_metadata.get("Item", [])
            
            # Extract useful information
            transaction_details = {}
            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                if name:
                    transaction_details[name] = value
            
            print(f"Transaction details: {transaction_details}")
            
            # Store success message and details in session
            session["mpesa_message"] = "Payment successful!"
            session["mpesa_status"] = "success"
            session["transaction_details"] = transaction_details
            
        else:
            # Payment failed
            session["mpesa_message"] = f"Payment failed: {result_desc}"
            session["mpesa_status"] = "failed"
            print(f"Payment failed: {result_desc}")
            
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error processing callback: {e}")
        session["mpesa_message"] = "Error processing payment callback."
        session["mpesa_status"] = "failed"
    
    # M-Pesa expects a simple response confirming receipt
    return "OK", 200

@app.route('/payment_status')
def payment_status():
    """API endpoint to check payment status (for AJAX polling)"""
    status = session.get("mpesa_status", "pending")
    message = session.get("mpesa_message", "Processing payment...")
    transaction_details = session.get("transaction_details", {})
    
    return jsonify({
        "status": status, 
        "message": message,
        "transaction_details": transaction_details
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Server is running"
    })

if __name__ == '__main__':
    app.run(debug=True)