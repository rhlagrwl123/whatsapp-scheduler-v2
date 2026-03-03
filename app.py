import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
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

HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RemindMe 💬</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{background:#f0ebe1;font-family:'Outfit',sans-serif;color:#1a1a1a;min-height:100vh}
.app{max-width:420px;margin:0 auto;padding:0 0 80px}
header{padding:40px 20px 20px;display:flex;justify-content:space-between;align-items:flex-start}
.logo{font-size:1.7rem;font-weight:800;letter-spacing:-0.03em}
.logo span{color:#25D366}
.sub{font-size:0.65rem;color:#999;letter-spacing:0.12em;margin-top:2px}
.pill{display:flex;align-items:center;gap:5px;background:#fff;border:1px solid #e0d8c8;padding:5px 12px;border-radius:99px;font-size:0.7rem;color:#999}
.dot{width:7px;height:7px;border-radius:50%;background:#ccc;transition:.3s}
.dot.on{background:#25D366;box-shadow:0 0 6px #25D366}
.box{margin:0 20px 20px;background:#25D366;border-radius:22px;padding:22px;box-shadow:0 8px 28px rgba(37,211,102,.28);position:relative;overflow:hidden}
.box::after{content:"💬";position:absolute;right:-8px;bottom:-12px;font-size:6rem;opacity:.1;transform:rotate(-15deg)}
.lbl{font-size:0.65rem;font-weight:700;color:rgba(0,0,0,.45);letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px}
textarea{width:100%;background:rgba(255,255,255,.28);border:1.5px solid rgba(255,255,255,.45);border-radius:12px;padding:12px 14px;font-family:'Outfit',sans-serif;font-size:1rem;font-weight:600;color:#000;resize:none;outline:none;min-height:76px;line-height:1.5}
textarea::placeholder{color:rgba(0,0,0,.38);font-weight:400}
textarea:focus{background:rgba(255,255,255,.42);border-color:rgba(255,255,255,.8)}
.pv{background:rgba(255,255,255,.48);border:1.5px solid rgba(255,255,255,.6);border-radius:12px;padding:12px 14px;margin-top:10px;display:none}
.pv.show{display:block;animation:up .3s}
.pv-title{font-weight:700;font-size:.9rem;margin-bottom:3px}
.pv-time{font-size:.75rem;color:rgba(0,0,0,.55);margin-bottom:6px}
.pv-msg{font-size:.75rem;background:#fff;border-radius:8px;padding:7px 10px;color:#444}
.err{background:#fff0f0;border:1.5px solid #fbb;border-radius:10px;padding:10px 14px;margin-top:8px;font-size:.8rem;color:#e33;display:none}
.err.show{display:block}
.btn{width:100%;margin-top:10px;background:#000;color:#fff;border:none;border-radius:12px;padding:15px;font-size:.95rem;font-weight:700;font-family:'Outfit',sans-serif;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:opacity .15s}
.btn:disabled{opacity:.5}
.chips-wrap{padding:0 20px 20px}
.chips-lbl{font-size:.65rem;color:#999;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{background:#fff;border:1.5px solid #e0d8c8;padding:7px 13px;border-radius:99px;font-size:.75rem;cursor:pointer;font-family:'Outfit',sans-serif;font-weight:600}
.chip:active{background:#dcf8c6;border-color:#25D366}
.list-wrap{padding:0 20px}
.list-title{font-size:1.05rem;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.cnt{background:#25D366;color:#fff;width:21px;height:21px;border-radius:50%;font-size:.7rem;display:flex;align-items:center;justify-content:center;font-weight:700}
.card{background:#fff;border:1.5px solid #e8e0d0;border-radius:16px;padding:14px 16px;margin-bottom:10px;animation:up .3s}
.card.sent{border-color:#25D366;background:#f2fdf4}
.card.failed{border-color:#f44;background:#fff5f5}
.ct{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:5px}
.ctitle{font-weight:700;font-size:.9rem;flex:1;padding-right:6px}
.tag{font-size:.6rem;font-weight:700;padding:2px 7px;border-radius:99px;text-transform:uppercase}
.ts{background:#fff3cd;color:#856404}
.tok{background:#dcf8c6;color:#128C7E}
.tf{background:#ffe0e0;color:#e33}
.ctime{font-size:.74rem;color:#888;margin-bottom:5px}
.cmsg{font-size:.74rem;color:#555;background:#f5f0e8;padding:7px 10px;border-radius:8px;line-height:1.4}
.cfoot{display:flex;justify-content:space-between;align-items:center;margin-top:8px}
.cd{font-size:.7rem;color:#25D366;font-weight:700}
.cd.late{color:#f44}
.del{background:none;border:none;color:#ccc;cursor:pointer;font-size:.95rem;padding:3px 7px}
.empty{text-align:center;padding:36px 20px;color:#bbb}
.empty-i{font-size:2.8rem;margin-bottom:10px}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(80px);background:#1a1a1a;color:#fff;padding:11px 18px;border-radius:99px;font-size:.82rem;transition:transform .3s;z-index:99;white-space:nowrap;max-width:90vw;text-align:center}
.toast.show{transform:translateX(-50%) translateY(0)}
.toast.ok{background:#128C7E}
.toast.bad{background:#e33}
.spin{width:17px;height:17px;border:2.5px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
</style></head>
<body>
<div class="app">
  <header>
    <div><div class="logo">Remind<span>Me</span></div><div class="sub">WHATSAPP SCHEDULER</div></div>
    <div class="pill"><div class="dot" id="dot"></div><span id="stxt">checking...</span></div>
  </header>

  <div class="box">
    <div class="lbl">✦ What do you want to remember?</div>
    <textarea id="inp" rows="3" placeholder="Call mom tomorrow at 7 PM&#10;Medicine today at 9 AM&#10;Meeting Friday 11am"></textarea>
    <div class="pv" id="pv"><div class="pv-title" id="pvT"></div><div class="pv-time" id="pvD"></div><div class="pv-msg" id="pvM"></div></div>
    <div class="err" id="err"></div>
    <button class="btn" id="btn" onclick="go()"><span id="btxt">Schedule Reminder →</span></button>
  </div>

  <div class="chips-wrap">
    <div class="chips-lbl">Quick add</div>
    <div class="chips">
      <div class="chip" onclick="s('Call mom tomorrow at 7 PM')">📞 Call mom</div>
      <div class="chip" onclick="s('Take medicine today at 9 PM')">💊 Medicine</div>
      <div class="chip" onclick="s('Team standup tomorrow at 10 AM')">👥 Standup</div>
      <div class="chip" onclick="s('Gym today at 6:30 PM')">🏋️ Gym</div>
      <div class="chip" onclick="s('Pay bills this Friday at 11 AM')">💳 Bills</div>
    </div>
  </div>

  <div class="list-wrap">
    <div class="list-title">Scheduled <div class="cnt" id="cnt">0</div></div>
    <div id="list"><div class="empty"><div class="empty-i">🔔</div><div>No reminders yet.<br>Type something above!</div></div></div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
const ANTHROPIC="https://api.anthropic.com/v1/messages";
let items=JSON.parse(localStorage.getItem("rm")||"[]");
window.onload=()=>{ping();render();setInterval(render,60000)};
async function ping(){try{const r=await fetch("/",{signal:AbortSignal.timeout(5000)});if(r.ok){document.getElementById("dot").className="dot on";document.getElementById("stxt").textContent="server live"}}catch{document.getElementById("stxt").textContent="offline"}}
function s(t){document.getElementById("inp").value=t}
async function go(){
  const prompt=document.getElementById("inp").value.trim();
  if(!prompt)return;
  const btn=document.getElementById("btn"),btxt=document.getElementById("btxt"),pv=document.getElementById("pv"),err=document.getElementById("err");
  pv.classList.remove("show");err.classList.remove("show");
  btn.disabled=true;btxt.innerHTML='<div class="spin"></div>';
  try{
    const today=new Date();
    const res=await fetch(ANTHROPIC,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:800,
        messages:[{role:"user",content:`Today is ${today.toLocaleDateString("en-IN",{weekday:"long",year:"numeric",month:"long",day:"numeric"})}. Time: ${today.toLocaleTimeString("en-IN")}.\nParse this reminder and return ONLY valid JSON no markdown:\n"${prompt}"\n{"title":"short task","message":"friendly WhatsApp msg with emoji","datetime":"YYYY-MM-DD HH:MM","date_display":"e.g. Tomorrow 5th March","time_display":"e.g. 7:00 PM","valid":true,"error":null}`}]})});
    const data=await res.json();
    const text=data.content.map(i=>i.text||"").join("");
    const p=JSON.parse(text.replace(/```json|```/g,"").trim());
    if(!p.valid){err.textContent="⚠ "+(p.error||"Could not understand. Try: Call mom tomorrow at 7 PM");err.classList.add("show");return}
    document.getElementById("pvT").textContent=p.title;
    document.getElementById("pvD").textContent="📅 "+p.date_display+"  ·  ⏰ "+p.time_display;
    document.getElementById("pvM").textContent=p.message;
    pv.classList.add("show");
    btxt.textContent="Sending...";
    const r2=await fetch("/add",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:p.message,datetime:p.datetime})});
    if(!r2.ok){const e=await r2.json();throw new Error(e.error||"Server error")}
    const d2=await r2.json();
    items.unshift({id:d2.reminder.id,title:p.title,message:p.message,datetime:p.datetime,date_display:p.date_display,time_display:p.time_display,status:"scheduled"});
    localStorage.setItem("rm",JSON.stringify(items));
    render();
    document.getElementById("inp").value="";
    pv.classList.remove("show");
    toast("✅ Reminder set for "+p.time_display,"ok");
  }catch(e){err.textContent="⚠ "+e.message;err.classList.add("show");toast(e.message,"bad")}
  finally{btn.disabled=false;btxt.textContent="Schedule Reminder →"}
}
function until(dt){
  const diff=new Date(dt.replace(" ","T"))-new Date();
  if(diff<0)return"overdue";
  const h=Math.floor(diff/3600000),m=Math.floor((diff%3600000)/60000);
  if(h>48)return"in "+Math.floor(h/24)+"d";
  if(h>0)return"in "+h+"h "+m+"m";
  return"in "+m+"m"
}
function render(){
  document.getElementById("cnt").textContent=items.length;
  const list=document.getElementById("list");
  if(!items.length){list.innerHTML='<div class="empty"><div class="empty-i">🔔</div><div>No reminders yet.<br>Type something above!</div></div>';return}
  list.innerHTML=items.map(r=>{
    const u=until(r.datetime),late=u==="overdue";
    const tc=r.status==="sent"?"tok":r.status==="failed"?"tf":"ts";
    const cc=r.status==="sent"?"sent":r.status==="failed"?"failed":"";
    return`<div class="card ${cc}"><div class="ct"><div class="ctitle">${r.title}</div><div class="tag ${tc}">${r.status}</div></div><div class="ctime">📅 ${r.date_display} · ⏰ ${r.time_display}</div><div class="cmsg">${r.message}</div><div class="cfoot"><div class="cd ${late?"late":""}">${late?"⚠ overdue":"⏳ "+u}</div><button class="del" onclick="del('${r.id}')">🗑</button></div></div>`
  }).join("")
}
async function del(id){
  try{await fetch("/delete/"+id,{method:"DELETE"})}catch{}
  items=items.filter(r=>r.id!==id);
  localStorage.setItem("rm",JSON.stringify(items));
  render();toast("Deleted")
}
function toast(msg,type=""){
  const t=document.getElementById("toast");
  t.textContent=msg;t.className="toast "+(type==="ok"?"ok":type==="bad"?"bad":"")+" show";
  setTimeout(()=>t.className="toast "+(type==="ok"?"ok":type==="bad"?"bad":""),3000)
}
</script>
</body></html>"""

@app.route("/", methods=["GET"])
def home():
    if request.headers.get("Accept", "").find("text/html") != -1:
        return render_template_string(HTML)
    return jsonify({
        "status": "✅ Scheduler is running",
        "twilio_sid_set": bool(os.getenv("TWILIO_ACCOUNT_SID")),
        "your_number_set": bool(os.getenv("YOUR_WHATSAPP_NUMBER")),
        "total_reminders": len(reminders),
        "reminders": list(reminders.values()),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/app", methods=["GET"])
def web_app():
    return render_template_string(HTML)

@app.route("/add", methods=["POST"])
def add_reminder():
    data = request.get_json()
    if not data or "message" not in data or "datetime" not in data:
        return jsonify({"error": "Send message and datetime (YYYY-MM-DD HH:MM)"}), 400
    try:
        run_at = datetime.strptime(data["datetime"], "%Y-%m-%d %H:%M")
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
