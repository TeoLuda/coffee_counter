import os
import json
import secrets
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template
from supabase import create_client

import requests

app = Flask(__name__)

SUPABASE_URL = "https://vybtsrmxrhqlplpaotkq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5YnRzcm14cmhxbHBscGFvdGtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyNzA5MDMsImV4cCI6MjA5NDg0NjkwM30.v1JZ06whw0CvgchJRC62s0fbG-21Yp3qvLLp_eoIiVc"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

COFFEE_PRICE = 0.50

TOKEN_EXPIRATION_HOURS = 24

PENDING_FILE = "pending_payments.json"

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME")

BASE_URL = "https://coffee-counter-292q.onrender.com"

def load_pending():

    if not os.path.exists(PENDING_FILE):
        return {}

    try:
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_pending(data):

    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, indent=4)

HISTORY_FILE = "payment_history.json"


def load_history():

    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_history(history):

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def send_payment_email(user, token):

    confirmation_link = f"{BASE_URL}/confirm/{token}"

    amount = user["coffee_count"] * COFFEE_PRICE

    payload = {

        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL
        },

        "to": [{
            "email": user["email"],
            "name": user["name"]
        }],

        "subject": "IPP Coffee Counter Payment",

        "htmlContent": f"""

<h2>☕ IPP Coffee Counter</h2>

<p>Hello <b>{user["name"]}</b>,</p>

<p>
You requested to mark your coffee payment as completed.
</p>

<p>

<b>Coffees:</b> {user["coffee_count"]}<br>
<b>Amount:</b> €{amount:.2f}

</p>

<p>

Please send the payment to:

</p>

<p>

<b>https://paypal.me/Teoluda</b>

</p>

<p>

<a href="{confirmation_link}"
style="
background:#8B5A2B;
color:white;
padding:12px 24px;
text-decoration:none;
border-radius:8px;
">

Confirm Payment

</a>

</p>

<p>

This link expires after 24 hours.

</p>

"""

    }

    headers = {

        "accept":"application/json",

        "api-key":BREVO_API_KEY,

        "content-type":"application/json"

    }

    r = requests.post(

        "https://api.brevo.com/v3/smtp/email",

        headers=headers,

        json=payload

    )

    return r.status_code == 201

@app.route("/request_payment/<int:user_id>", methods=["POST"])
def request_payment(user_id):

    response = (
        supabase
        .table("users")
        .select("*")
        .eq("id", user_id)
        .execute()
    )

    if len(response.data) == 0:
        return jsonify({"status":"error"})

    user = response.data[0]

    token = secrets.token_urlsafe(32)

    pending = load_pending()

    pending[token] = {

        "user_id": user_id,

        "created_at": datetime.utcnow().isoformat()

    }

    save_pending(pending)

    success = send_payment_email(user, token)

    if success:

        return jsonify({
            "status":"ok"
        })

    else:

        return jsonify({
            "status":"email_error"
        })

@app.route("/")
def dashboard():

    response = (
        supabase
        .table("users")
        .select("*")
        .order("name")
        .execute()
    )

    users = response.data

    for user in users:
        user["amount"] = round(user["coffee_count"] * COFFEE_PRICE, 2)

    history = load_history()

    return render_template(
        "index.html",
        users=users,
        history=history,
        coffee_price=COFFEE_PRICE,
        paypal_link="https://paypal.me/Teoluda"
    )

@app.route("/coffee", methods=["POST"])
def coffee():

    data = request.json

    uid = data["uid"].replace(" ", "").strip().upper()

    print("UID received:", uid)

    response = supabase.table("users") \
        .select("*") \
        .eq("nfc_uid", uid) \
        .execute()

    users = response.data

    # USER NOT FOUND
    if len(users) == 0:

        new_user = {
            "created_at": "Now",
            "name": "Unknown",
            "nfc_uid": uid,
            "coffee_count": 1
        }

        insert_response = supabase.table("users") \
            .insert(new_user) \
            .execute()

        created_user = insert_response.data[0]

        return jsonify({
            "status": "new_user",
            "user": created_user
        })

    # USER FOUND
    user = users[0]

    new_count = user["coffee_count"] + 1

    update_response = supabase.table("users") \
        .update({
            "coffee_count": new_count
        }) \
        .eq("id", user["id"]) \
        .execute()

    return jsonify({
        "status": "ok",
        "name": user["name"],
        "coffee_count": new_count
    })
    
@app.route("/confirm/<token>")
def confirm_payment(token):

    pending = load_pending()

    if token not in pending:
        return """
        <h2>Invalid or expired link.</h2>
        """

    payment = pending[token]

    created = datetime.fromisoformat(payment["created_at"])

    if datetime.utcnow() - created > timedelta(hours=TOKEN_EXPIRATION_HOURS):

        del pending[token]
        save_pending(pending)

        return """
        <h2>This confirmation link has expired.</h2>
        """

    user_id = payment["user_id"]

    response = (
        supabase
        .table("users")
        .select("*")
        .eq("id", user_id)
        .execute()
    )

    if len(response.data) == 0:
        return "<h2>User not found.</h2>"

    user = response.data[0]

    history = load_history()

    history.append({

        "date": datetime.utcnow().isoformat(),

        "name": user["name"],

        "email": user["email"],

        "coffees": user["coffee_count"],

        "amount": round(user["coffee_count"] * COFFEE_PRICE, 2)

    })

    save_history(history)

    supabase.table("users").update({

        "coffee_count":0

    }).eq("id", user_id).execute()

    del pending[token]

    save_pending(pending)

    return f"""
<!DOCTYPE html>
<html>

<head>

<title>Payment confirmed</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

</head>

<body style="background:#f5f5f5;">

<div class="container">

<div class="card mt-5 mx-auto" style="max-width:650px;border-radius:18px;">

<div class="card-body text-center p-5">

<h1>☕</h1>

<h2>Payment confirmed!</h2>

<br>

<p>

Thank you <b>{user["name"]}</b>.

</p>

<p>

Your payment has been confirmed successfully.

</p>

<p>

Your coffee counter has been reset to <b>0 coffees</b>.

</p>

<a href="/" class="btn btn-dark">

Back to dashboard

</a>

</div>

</div>

</div>

</body>

</html>
"""

#if __name__ == "__main__":
#    app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
