import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
scheduler = BackgroundScheduler()
reminders = {}

def get_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        raise ValueError("Twilio credentials not set")
    return Client(sid, token)

def get_your_number():
    return os.getenv("YOUR_WHATSAPP_NUMBER", "")

TWILIO_NUMBER = "+14155238886"

def send_whatsapp(rid, message):
    try:
        client = get_client()
        client.messages.create(
            from_=f"whatsapp:{TWILIO_NUMBER}",
            to=f"whatsapp:{get_your_number()}",
            body=message,
        )
        if rid in reminders:
            reminders[rid]["status"] = "sent"
        log.info(f"✅ Sent [{rid}]: {message}")
    except Exception as e:
        if rid in reminders:
            reminders[rid]["status"] = "failed"
        log.error(f"❌ Failed [{rid}]: {e}")

def keep_alive():
    try:
        client = get_client()
        client.messages.create(
            from_=f"whatsapp:{TWILIO_NUMBER}",
            to=f"whatsapp:{get_your_number()}",
            body="🤖 Your reminder scheduler is running fine!",
        )
        log.info("💓 Keep-alive sent")
    except Exception as e:
        log.warning(f"Keep-alive failed: {e}")

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ Scheduler is running",
        "twilio_sid_set": bool(os.getenv("TWILIO_ACCOUNT_SID")),
        "your_number_set": bool(os.getenv("YOUR_WHATSAPP_NUMBER")),
        "total_reminders": len(reminders),
        "reminders": list(reminders.values()),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/add", methods=["POST"])
def add_reminder():
    data = request.get_json()
    if not data or "message" not in data or "datetime" not in data:
        return jsonify({"error": "Send 'message' and 'datetime' (YYYY-MM-DD HH:MM)"}), 400
    try:
        run_at = datetime.strptime(data["datetime"], "%Y-%m-%d %H:%MM")
    except ValueError:
        return jsonify({"error": "Use format: YYYY-MM-DD HH:MM"}), 400
    if run_at < datetime.now():
        return jsonify({"error": "That time is already in the past!"}), 400

    rid = str(int(datetime.now().timestamp() * 1000))
    reminders[rid] = {"id": rid, "message": data["message"], "datetime": data["datetime"], "status": "scheduled"}
    scheduler.add_job(send_whatsapp, 'date', run_date=run_at, args=[rid, data["message"]], id=rid)
    log.info(f"📅 Scheduled [{rid}] at {run_at}")
    return jsonify({"success": True, "reminder": reminders[rid]}), 201

@app.route("/list", methods=["GET"])
def list_reminders():
    return jsonify(list(reminders.values()))

@app.route("/delete/<rid>", methods=["DELETE"])
def delete_reminder(rid):
    if rid not in reminders:
        return jsonify({"error": "Not found"}), 404
    try:
        scheduler.remove_job(rid)
    except Exception:
        pass
    del reminders[rid]
    return jsonify({"success": True})

if __name__ == "__main__":
    scheduler.add_job(keep_alive, 'interval', hours=20, id="keep_alive")
    scheduler.start()
    log.info("🚀 Scheduler started!")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
