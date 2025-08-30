from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------------------------
# Load users and FAQ data
# ---------------------------
with open("users.json") as f:
    users = json.load(f)

with open("faq.json") as f:
    faq_data = json.load(f)

# ---------------------------
# Attendance JSON storage
# ---------------------------
ATTENDANCE_FILE = "attendance.json"

# Ensure the attendance file exists
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, "w") as f:
        json.dump({}, f)

def load_attendance():
    with open(ATTENDANCE_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    return data

def save_attendance(data):
    with open(ATTENDANCE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username]["password"] == password:
            session["user"] = username
            return redirect(url_for("chat"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)

# Chat page
@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", username=session["user"])

# Attendance page
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_attendance()
    user_logs = data.get(username, [])

    message = None
    disable_button = False
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if attendance already marked today
    for log in user_logs:
        log_date = log["time"].split(" ")[0]
        if log["type"] == "attendance" and log_date == today:
            disable_button = True
            message = f"❌ You have already marked attendance today."
            break

    # Mark attendance
    if request.method == "POST" and not disable_button:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_logs.append({
            "type": "attendance",
            "time": now
        })
        data[username] = user_logs
        save_attendance(data)
        message = f"✅ Attendance marked for today!"
        disable_button = True

    return render_template(
        "attendance.html",
        username=username,
        records=[log for log in user_logs if log["type"] == "attendance"],
        message=message,
        disable_button=disable_button,
        today=today
    )

# Leaves page with reason box
@app.route("/leaves", methods=["GET", "POST"])
def leaves():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_attendance()
    user_logs = data.get(username, [])

    today = datetime.now()
    month_str = today.strftime("%Y-%m")  # YYYY-MM
    message = None

    # Count leaves this month
    leaves_this_month = sum(1 for log in user_logs
                            if log["type"] == "leave" and log["time"].startswith(month_str))

    disable_button = leaves_this_month >= 5

    if request.method == "POST" and not disable_button:
        reason = request.form.get("reason", "").strip()
        if not reason:
            message = "❌ Please provide a reason for your leave."
        else:
            leave_entry = {
                "type": "leave",
                "time": today.strftime("%Y-%m-%d"),
                "reason": reason
            }
            user_logs.append(leave_entry)
            data[username] = user_logs
            save_attendance(data)
            leaves_this_month += 1
            message = f"✅ Leave approved! You have used {leaves_this_month}/5 leaves this month."
            disable_button = leaves_this_month >= 5

    return render_template(
        "leaves.html",
        username=username,
        records=[log for log in user_logs if log["type"] == "leave"],
        message=message,
        disable_button=disable_button,
        month=today.strftime("%B %Y"),
        leaves_used=leaves_this_month
    )

# Chatbot response
@app.route("/get", methods=["POST"])
def get_bot_response():
    if "user" not in session:
        return jsonify({"bot": "Please log in first."})

    user_text = request.form["user_input"].lower()

    if "leave" in user_text:
        bot_response = faq_data.get("leave_policy", "Sorry, I don't know that.")
    elif "overtime" in user_text:
        bot_response = faq_data.get("overtime_policy", "Sorry, I don't know that.")
    elif "work hours" in user_text or "working hours" in user_text:
        bot_response = faq_data.get("work_hours", "Sorry, I don't know that.")
    elif "dress code" in user_text or "dress" in user_text:
        bot_response = faq_data.get("dress_code", "Sorry, I don't know that.")
    elif "remote" in user_text or "work from home" in user_text:
        bot_response = faq_data.get("remote_work", "Sorry, I don't know that.")
    else:
        bot_response = "Sorry, I don't know the answer yet."

    return jsonify({"bot": bot_response})

# Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ---------------------------
# Run the app
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
