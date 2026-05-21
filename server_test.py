from flask import Flask, request, jsonify
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = "https://vybtsrmxrhqlplpaotkq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5YnRzcm14cmhxbHBscGFvdGtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyNzA5MDMsImV4cCI6MjA5NDg0NjkwM30.v1JZ06whw0CvgchJRC62s0fbG-21Yp3qvLLp_eoIiVc"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

response = supabase.table("users").select("*").execute()

print(response.data)

import requests

response = requests.post(
    "http://127.0.0.1:5000/coffee",
    json={
        "uid": "41ECAA81392"
    }
)

print(response.json())
