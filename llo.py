from flask import Flask, session
from flask_session import Session

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'   
Session(app)


data = {'Body': {'stkCallback': {'MerchantRequestID': 'c673-495c-a417-9fe538db519214413', 'CheckoutRequestID': 'ws_CO_310720251822301797210158', 'ResultCode': 2001, 'ResultDesc': 'The initiator information is invalid.'}}}

with app.test_request_context('/'):
    session.clear()  # Clear the session to avoid conflicts
    result_code = data["Body"]["stkCallback"]["ResultCode"]
    result_desc = data["Body"]["stkCallback"]["ResultDesc"]


    if result_code == 0:
        session["mpesa_message"] = "Payment successful!"
        session["mpesa_status"] = "success"
    else:
        session["mpesa_message"] = f"Payment failed: {result_desc}"
        session["mpesa_status"] = "failed"

    sessionnow = session.get("mpesa_status")
    messagenow = session.get("mpesa_message")

    print("Result Code:", result_code, "Result Description:", result_desc, "Session Status:", sessionnow, "Message:", messagenow)   
