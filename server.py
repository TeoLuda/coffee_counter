from flask import Flask, request, jsonify
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = "https://vybtsrmxrhqlplpaotkq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5YnRzcm14cmhxbHBscGFvdGtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyNzA5MDMsImV4cCI6MjA5NDg0NjkwM30.v1JZ06whw0CvgchJRC62s0fbG-21Yp3qvLLp_eoIiVc"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)



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
    
if __name__ == "__main__":
    app.run(debug=True)
