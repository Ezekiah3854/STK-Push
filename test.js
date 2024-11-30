const express = require("express");
const axios = require("axios");
const bodyParser = require("body-parser");
const dotenv = require("dotenv");
const path = require("path");
const port = 3400;
const app = express();

dotenv.config();

app.set("view engine", "ejs");
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(bodyParser.urlencoded({ extended: false }));
app.use(express.static(path.join(__dirname, "assets")));

app.get("/", (req, res) => {
  // Check query params for alert visibility and message
  const alertVisible = req.query.alertVisible === "true";
  const confirmation = req.query.message || "";
  const initiatedSuccess = req.query.initiatedSuccess || null;
  const payedSuccess = req.query.payedSuccess || null;

  res.render("index", { alertVisible, confirmation, initiatedSuccess, payedSuccess });
});

// Generate Access Token
async function getAccessToken() {
  const auth = Buffer.from(
    `${process.env.MPESA_CONSUMER_KEY}:${process.env.MPESA_CONSUMER_SECRET}`
  ).toString("base64");

  const response = await axios.get(
    "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
    { headers: { Authorization: `Basic ${auth}` } }
  );

  return response.data.access_token;
}

// Handle STK Push
app.post("/api/pay", async (req, res) => {
  const phoneNo = req.body.phone.substring(1);
  const amount = req.body.amount;
  const phone = `254${phoneNo}`;
  const accessToken = await getAccessToken();

  const timestamp = new Date().toISOString().replace(/[^0-9]/g, "").slice(0, 14);
  const password = Buffer.from(
    `${process.env.MPESA_SHORTCODE}${process.env.MPESA_PASSKEY}${timestamp}`
  ).toString("base64");
  const accountReference = "BeamerWiFi";

  const requestData = {
    BusinessShortCode: process.env.MPESA_SHORTCODE,
    Password: password,
    Timestamp: timestamp,
    TransactionType: "CustomerPayBillOnline",
    Amount: amount,
    PartyA: phone,
    PartyB: process.env.MPESA_SHORTCODE,
    PhoneNumber: phone,
    CallBackURL: process.env.CALLBACK_URL,
    AccountReference: accountReference,
    TransactionDesc: "Payment for Order",
  };

  try {
    await axios.post(
      "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
      requestData,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );

    res.redirect(
      `/?alertVisible=true&message=Payment initiated, check your phone to complete.&initiatedSuccess=done`
    );
  } catch (error) {
    console.error("Error in STK Push:", error.response ? error.response.data : error);
    res.redirect(
      `/?alertVisible=true&message=Error initiating payment. Please try again.&initiatedSuccess=failed`
    );
  }
});

app.post("/callBack", (req, res) => {
  const callbackData = req.body;

  // Check ResultCode to determine success or failure
  if (callbackData.Body.stkCallback.ResultCode === 0) {
    console.log("Payment successful!");
    // Redirect user to the main page with success alert
    res.redirect(
      `/?alertVisible=true&message=Payment successful!&payedSuccess=done`
    );
  } else {
    console.log("Payment failed:", callbackData.Body.stkCallback.ResultDesc);
    // Redirect user to the main page with failure alert
    res.redirect(
      `/?alertVisible=true&message=Payment unsuccessful. Please try again.&payedSuccess=failed`
    );
  }

  // Acknowledge receipt of callback (this is required by Safaricom)
  res.status(200).send("Callback received");
});

// Start server
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});
