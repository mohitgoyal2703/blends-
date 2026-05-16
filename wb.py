import telebot, time, json, base64, hmac, hashlib, random, string, urllib.parse, threading, sys, os, re
from curl_cffi import requests
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))
def now_ist(): return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')
CONFIG_FILE, config_data = "config.json", {"TELEGRAM_TOKEN": "", "ADMIN_ID": "", "AUTHORIZED_USERS": [], "BROADCAST_CHANNEL": None}
def save_config():
    with open(CONFIG_FILE, "w") as f: json.dump(config_data, f, indent=4)
print("==========================================\n   Fleet Commander Bot - Auto-Bypass Edition\n==========================================")
config_data["TELEGRAM_TOKEN"] = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_TOKEN = config_data["TELEGRAM_TOKEN"]

startup_max_spins = int(os.getenv("MAX_SPINS", "50"))





ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_ID", "").split(",")
    if x.strip()
]

ADMIN_ID = ADMIN_IDS[0]
    
print("\n✅ Authorization Successful. Booting systems...")
PINCODE = "110021"
bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_state = {"max_spins": startup_max_spins, "username": "Commander"}
bot_config = {"cf_clearance": None, "user_agent": None, "cloudflare_blocked": False}
active_sessions, retry_sessions, history_log, system_logs = {}, {}, [], []
MAX_CONCURRENT_LOOPS, active_loops_count, active_users = 20, 0, set()
user_cancel_flags, bot_paused, last_api_response, status_msg_ids = {}, False, {}, {}
def log_event(message, is_error=False):
    print(message)
    if len(system_logs) > 500: system_logs.pop(0)
    system_logs.append(f"[{now_ist()}] {message}")
    if is_error:
        try: bot.send_message(ADMIN_ID, f"⚠️ <b>SYSTEM ERROR</b>\n\n<code>{message}</code>", parse_mode="HTML")
        except: pass

def is_authorized(user_id):
    return user_id in ADMIN_IDS
def record_history(chat_id, phone, status, reward="None", tries=0):
    history_log.append({"chat_id": chat_id, "phone": phone, "status": status, "reward": reward, "tries": tries, "timestamp": now_ist()})
def save_session(chat_id, phone, master_key, user_key, data_key, access_token, spin_count=0):
    active_sessions[chat_id] = {"phone": phone, "master_key": master_key, "user_key": user_key, "data_key": data_key, "access_token": access_token, "spin_count": spin_count}
def update_spin_count(chat_id, spin_count):
    if chat_id in active_sessions: active_sessions[chat_id]["spin_count"] = spin_count
def remove_session(chat_id): active_sessions.pop(chat_id, None)
def decode_response(encoded_str):
    try:
        pad = len(encoded_str) % 4
        if pad > 0: encoded_str += "=" * (4 - pad)
        return json.loads(base64.b64decode(encoded_str).decode('utf-8'))
    except Exception: return {}
def generate_signed_payload(data_dict, data_key):
    timestamp = int(time.time() * 1000)
    data_dict['t'] = timestamp
    part1 = base64.b64encode(str(timestamp).encode()).decode()
    json_str = json.dumps(data_dict, separators=(',', ':'))
    part2 = base64.b64encode(json_str.encode()).decode()
    actual_secret = data_key[4:18]
    signature_hex = hmac.new(actual_secret.encode(), f"{part1}.{part2}".encode(), hashlib.sha256).hexdigest()
    f = base64.b64encode(signature_hex.encode()).decode()
    m, k = random.randint(1, 6), random.randint(2, 6)
    h = ''.join(random.choices(string.ascii_letters + string.digits, k=k))
    part3 = f"{k}{m}{f[:m]}{h}{f[m:]}"
    return f"{urllib.parse.quote_plus(part1)}.{urllib.parse.quote_plus(part2)}.{urllib.parse.quote_plus(part3)}", timestamp
class DiscoverWorldBot:
    def __init__(self):
        self.session = requests.Session(impersonate="chrome120")
        self.base_headers = {'accept-language': 'en-US,en;q=0.9', 'dnt': '1'}
        if bot_config['user_agent']:
            self.base_headers['user-agent'] = bot_config['user_agent']
            try:
                ver = bot_config['user_agent'].split("Chrome/")[1].split(".")[0]
                self.base_headers['sec-ch-ua'] = f'"Google Chrome";v="{ver}", "Not.A/Brand";v="8", "Chromium";v="{ver}"'
                self.base_headers['sec-ch-ua-mobile'], self.base_headers['sec-ch-ua-platform'] = '?0', '"Windows"'
            except: pass
        if bot_config['cf_clearance']: self.session.cookies.set('cf_clearance', bot_config['cf_clearance'], domain='discoverworldblends.in')
        self.session.headers.update(self.base_headers)
        self.master_key = self.user_key = self.data_key = self.access_token = None
    def load_state(self, mk, uk, dk, at):
        self.master_key, self.user_key, self.data_key, self.access_token = mk, uk, dk, at
        self.session.cookies.set('itc_discover_world_blends_master_key', self.master_key, domain='discoverworldblends.in')
    def harvest_master_key(self):
        try:
            self.session.get('https://discoverworldblends.in/', headers={'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8', 'sec-fetch-dest': 'document', 'sec-fetch-mode': 'navigate', 'sec-fetch-site': 'none', 'sec-fetch-user': '?1', 'upgrade-insecure-requests': '1'}, timeout=20)
            self.master_key = str(random.randint(1000000000, 9999999999))
            self.session.cookies.set('itc_discover_world_blends_master_key', self.master_key, domain='discoverworldblends.in')
            return True
        except Exception as e:
            log_event(f"Harvest Error: {e}", True)
            return False
    def collect_keys(self):
        try:
            headers = {'accept': 'application/json', 'content-type': 'application/json', 'origin': 'https://discoverworldblends.in', 'referer': 'https://discoverworldblends.in/', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin'}
            if self.access_token: headers['authorization'] = f"Bearer {self.access_token}"
            resp = self.session.post('https://discoverworldblends.in/api/collect', json={"masterKey": self.master_key}, headers=headers, timeout=20)
            data = decode_response(resp.json().get('resp', ''))
            if data.get('statusCode') == 200:
                self.user_key, self.data_key = data.get('userKey'), data.get('dataKey')
                return True
            return False
        except Exception as e:
            log_event(f"Collect Keys Error: {e}", True)
            return False
    def post_signed_data(self, url_path, payload):
        headers = {'accept': '*/*', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'origin': 'https://discoverworldblends.in', 'referer': 'https://discoverworldblends.in/', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin'}
        if self.access_token: headers['authorization'] = f"Bearer {self.access_token}"
        signed_data, ts = generate_signed_payload(payload, self.data_key)
        resp = self.session.post(f"https://discoverworldblends.in/api/users/{url_path}/{self.user_key}?t={ts + random.randint(3, 8)}", headers=headers, data=f"userKey={self.user_key}&data={signed_data}", timeout=20)
        return decode_response(resp.json().get('resp', ''))
    def fetch_pincode_data(self):
        data = self.post_signed_data("pinCode", {"pincode": PINCODE, "userKey": self.user_key})
        return data.get('state'), data.get('city')
    def register(self, phone, state, city):
        name = f"{random.choice(['Amit','Rahul','Priya','Neha','Vikas','Sneha','Karan','Anjali','Suresh','Pooja','Raj','Sunil','Kavita','Ramesh','Deepak','Rohan','Vikram','Snehal','Pankaj','Arun'])} {random.choice(['Kumar','Sharma','Singh','Gupta','Verma','Patil','Yadav','Jain','Mishra','Pandey','Chauhan','Bhatia','Reddy','Rao','Das'])}"
        return self.post_signed_data("register", {"name": name, "mobile": phone, "state": state, "city": city, "pincode": PINCODE, "agreeToTnc": True, "confirmAge": True, "userKey": self.user_key}).get('statusCode') == 200
    def verify_otp(self, otp):
        data = self.post_signed_data("verifyOTP", {"otp": otp, "userKey": self.user_key})
        if data.get('statusCode') == 200:
            self.access_token = data.get('accessToken')
            return True
        return False
@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not is_authorized(message.chat.id): return
    t = "🏴‍☠️ <b>Fleet Commander Dashboard</b>\n\n<b>Commands:</b>\n/start - Start voyage\n/tryset &lt;number&gt; - Set max spins\n/setcurl - Paste cURL\n/clearcurl - Revert to Clean Slate\n/status - View stats\n/numbers - Past numbers\n/cancel - Stop loop\n"
    if message.chat.id == ADMIN_ID: t += "\n👑 <b>Admin:</b>\n/auth &lt;id&gt; | /unauth &lt;id&gt;\n/running\n/setbroadcast &lt;id&gt;\n/pause | /resume\n/logs\n/restart"
    bot.reply_to(message, t, parse_mode="HTML")
@bot.message_handler(commands=['auth'])
def auth_cmd(message):
    if message.chat.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 2: return bot.reply_to(message, "Users:\n" + "\n".join([f"• <code>{u}</code>" for u in config_data.get("AUTHORIZED_USERS", [])]) if config_data.get("AUTHORIZED_USERS") else "No users.", parse_mode="HTML")
    try:
        t = int(p[1])
        if t not in ALLOWED_ADMINS: return bot.reply_to(message, "❌ Access Denied: This ID is not on the hardcoded license list.")
        if t not in config_data["AUTHORIZED_USERS"]: config_data["AUTHORIZED_USERS"].append(t); save_config()
        bot.reply_to(message, f"✅ User {t} granted access.")
    except ValueError: bot.reply_to(message, "❌ Invalid ID.")
@bot.message_handler(commands=['unauth'])
def unauth_cmd(message):
    if message.chat.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 2: return bot.reply_to(message, "⚠️ Usage: /unauth <ID>")
    try:
        t = int(p[1])
        if t in config_data["AUTHORIZED_USERS"]: config_data["AUTHORIZED_USERS"].remove(t); save_config(); bot.reply_to(message, f"🚫 User {t} removed.")
        else: bot.reply_to(message, "ℹ️ User not found.")
    except ValueError: bot.reply_to(message, "❌ Invalid ID.")
@bot.message_handler(commands=['setbroadcast'])
def setbroadcast_cmd(message):
    if message.chat.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 2: return bot.reply_to(message, f"Current: {config_data.get('BROADCAST_CHANNEL')}\nUsage: /setbroadcast <id> | none")
    if p[1].lower() == "none": config_data["BROADCAST_CHANNEL"] = None; save_config(); return bot.reply_to(message, "📴 Broadcast disabled.")
    try:
        cid = int(p[1])
        bot.delete_message(cid, bot.send_message(cid, "🔧").message_id)
        config_data["BROADCAST_CHANNEL"] = cid; save_config()
        bot.reply_to(message, f"📢 Set to {cid}.")
    except Exception as e: bot.reply_to(message, f"❌ Error: {e}")
@bot.message_handler(commands=['running'])
def running_cmd(message):
    if message.chat.id != ADMIN_ID: return
    l = [f"📞 <code>{d['phone']}</code> | ID: {c} | Spin {d['spin_count']}" for c, d in active_sessions.items() if d.get("access_token")]
    bot.reply_to(message, "🟢 <b>Active Voyages:</b>\n" + "\n".join(l) if l else "⚪ No active loops spinning.", parse_mode="HTML")
@bot.message_handler(commands=['setcurl'])
def setcurl_cmd(message):
    if not is_authorized(message.chat.id): return
    c = message.text[len('/setcurl '):].strip()
    if not c: return bot.reply_to(message, "⚠️ Usage: /setcurl <paste cURL>")
    cf, ua = re.search(r'cf_clearance=([^;\'"]+)', c), re.search(r'-H [\'"]user-agent: (.*?)[\'"]', c, re.I)
    if not cf: return bot.reply_to(message, "❌ No cf_clearance found.")
    bot_config['cf_clearance'], bot_config['cloudflare_blocked'] = cf.group(1), False
    if ua: bot_config['user_agent'] = ua.group(1)
    bot.reply_to(message, f"✅ <b>Bypass Configured!</b>\ncf_clearance: <code>{bot_config['cf_clearance'][:15]}...</code>" + (f"\nUA: <code>{bot_config['user_agent']}</code>" if ua else ""), parse_mode="HTML")
@bot.message_handler(commands=['clearcurl'])
def clearcurl_cmd(message):
    if not is_authorized(message.chat.id): return
    bot_config['cf_clearance'] = bot_config['user_agent'] = None
    bot.reply_to(message, "✅ Reverted to Clean Slate.")
@bot.message_handler(commands=['tryset'])
def tryset_cmd(message):
    if not is_authorized(message.chat.id): return
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit(): return bot.reply_to(message, "⚠️ Usage: /tryset <number>")
    user_state["max_spins"] = int(p[1])
    bot.reply_to(message, f"✅ Limit Updated to {p[1]}.")
@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    cid = message.chat.id
    if not is_authorized(cid): return
    if cid in active_users or cid in active_sessions:
        user_cancel_flags[cid] = True; remove_session(cid); active_users.discard(cid)
        bot.reply_to(message, "🛑 Cancellation sent.")
    else: bot.reply_to(message, "ℹ️ No active loops.")
def build_status_text(cid):
    a, uh = active_sessions.get(cid), [h for h in history_log if h.get("chat_id") == cid]
    m = f"📊 <b>Dashboard</b>\n⚙️ Max: {user_state['max_spins']}\n📈 Unique: {len(set(h['phone'] for h in uh))}\n🏆 Wins: {sum(1 for h in uh if h['status'] == 'Won')}\n🍪 Mode: {'Manual' if bot_config['cf_clearance'] else 'Clean Slate'}\n\n"
    if a and a.get("access_token"): m += f"🟢 <b>Running:</b> <code>{a['phone']}</code> ({a['spin_count']}/{user_state['max_spins']})\n<i>{now_ist()}</i>"
    elif a: m += f"🟡 <b>Pending OTP:</b> <code>{a['phone']}</code>"
    else: m += "⚪ <b>Running:</b> None"
    return m
@bot.message_handler(commands=['status'])
def status_cmd(message):
    if not is_authorized(message.chat.id): return
    s = bot.reply_to(message, build_status_text(message.chat.id), parse_mode="HTML")
    if message.chat.id in active_users: status_msg_ids[message.chat.id] = (message.chat.id, s.message_id)
@bot.message_handler(commands=['response'])
def response_cmd(message):
    if not is_authorized(message.chat.id): return
    resp = last_api_response.get(message.chat.id)
    if not resp: return bot.reply_to(message, "ℹ️ No API response recorded yet.", parse_mode="HTML")
    bot.reply_to(message, f"📡 <b>Last API Response:</b>\n<pre>{json.dumps(resp, indent=2)}</pre>", parse_mode="HTML")
@bot.message_handler(commands=['numbers'])
def numbers_cmd(message):
    if not is_authorized(message.chat.id): return
    uh = [h for h in history_log if h.get("chat_id") == message.chat.id]
    if not uh: return bot.reply_to(message, "No voyages.")
    m, c = f"📜 <b>Numbers ({len(uh)}):</b>\n\n", ""
    for r in reversed(uh):
        reward_text = f" - {r['reward']}" if r['status'] == 'Won' else ''
        l = f"📞 <code>{r['phone']}</code> | {r['tries']} spins | {r['status']}{reward_text}\n"
    if len(m) + len(c) + len(l) > 4000: bot.send_message(message.chat.id, m + c, parse_mode="HTML"); m, c = "", ""
    c += l
    if m or c: bot.send_message(message.chat.id, m + c, parse_mode="HTML")
@bot.message_handler(commands=['pause'])
def pause_bot(message):
    global bot_paused
    if message.chat.id == ADMIN_ID: bot_paused = True; bot.reply_to(message, "⏸️ Paused.")
@bot.message_handler(commands=['resume'])
def resume_bot(message):
    global bot_paused
    if message.chat.id == ADMIN_ID: bot_paused = False; bot.reply_to(message, "▶️ Resumed.")
@bot.message_handler(commands=['logs'])
def fetch_logs(message):
    if message.chat.id != ADMIN_ID: return
    if not system_logs: return bot.reply_to(message, "No logs.")
    o = ""
    for l in reversed(system_logs):
        if len(o) + len(l) > 4000: bot.send_message(ADMIN_ID, f"```\n{o}\n```", parse_mode="Markdown"); o = ""
        o += f"{l}\n"
    if o: bot.send_message(ADMIN_ID, f"```\n{o}\n```", parse_mode="Markdown")
@bot.message_handler(commands=['restart'])
def restart_bot(message):
    global active_loops_count
    if message.chat.id != ADMIN_ID: return
    active_loops_count = 0; active_users.clear(); active_sessions.clear(); retry_sessions.clear(); history_log.clear()
    for k in user_cancel_flags: user_cancel_flags[k] = True 
    log_event("SYSTEM RESTART.", False); bot.reply_to(message, "🔄 State cleared.")
@bot.message_handler(commands=['start'])
def start_cmd(message):
    cid = message.chat.id
    if message.chat.type != 'private': return bot.reply_to(message, "⚠️ Private chat only.")
    bot.clear_step_handler_by_chat_id(cid)
    if not is_authorized(cid): return bot.reply_to(message, "⛔ Access Denied.")
    if bot_paused and cid != ADMIN_ID: return bot.reply_to(message, "⏸️ Paused.")
    if cid in active_users:
        if active_sessions.get(cid, {}).get("access_token"): return bot.reply_to(message, "⚠️ Number already running.")
        else: remove_session(cid)
    user_cancel_flags[cid] = False
    if message.from_user.username: user_state['username'] = message.from_user.username
    bot.register_next_step_handler(bot.send_message(cid, f"🏴‍☠️ Send 10-digit number:\n<i>(Max spins: {user_state['max_spins']})</i>", parse_mode="HTML"), process_phone)
def process_phone(message):
    cid, t = message.chat.id, message.text.strip() if message.text else ""
    if t.startswith('/'): bot.clear_step_handler_by_chat_id(cid); return bot.process_new_messages([message])
    if len(t) != 10 or not t.isdigit(): return bot.register_next_step_handler(bot.send_message(cid, "Invalid format. Send 10 digits:"), process_phone)
    bot.send_message(cid, f"[*] Harvesting session for {t}...")
    ub = DiscoverWorldBot()
    if not ub.harvest_master_key() or not ub.collect_keys():
        if bot_config['cf_clearance']:
            bot_config['cf_clearance'] = bot_config['user_agent'] = None
            bot.send_message(cid, "⚠️ Cookie Expired. Retrying Clean Slate...")
            ub = DiscoverWorldBot()
            if not ub.harvest_master_key() or not ub.collect_keys(): return bot.send_message(cid, "🚨 <b>Blocked!</b> Use <code>/setcurl &lt;paste&gt;</code>", parse_mode="HTML")
        else: return bot.send_message(cid, "🚨 <b>Blocked!</b> Use <code>/setcurl &lt;paste&gt;</code>", parse_mode="HTML")
    state, city = ub.fetch_pincode_data()
    if not state: return bot.send_message(cid, "[-] Location failed.")
    if ub.register(t, state, city):
        save_session(cid, t, ub.master_key, ub.user_key, ub.data_key, "")
        bot.register_next_step_handler(bot.send_message(cid, "[+] SMS Sent! OTP:"), process_otp)
    else: bot.send_message(cid, "[-] Registration failed.")
def process_otp(message, attempts=1):
    cid, t = message.chat.id, message.text.strip() if message.text else ""
    if t.startswith('/'): bot.clear_step_handler_by_chat_id(cid); return bot.process_new_messages([message])
    sd = active_sessions.get(cid)
    if not sd: return bot.send_message(cid, "Session expired.")
    bot.send_message(cid, "[*] Verifying...")
    ub = DiscoverWorldBot(); ub.load_state(sd['master_key'], sd['user_key'], sd['data_key'], None)
    try:
        if ub.verify_otp(t):
            save_session(cid, sd['phone'], sd['master_key'], sd['user_key'], sd['data_key'], ub.access_token, 0)
            bot.send_message(cid, "✅ Granted! Spawning thread...")
            threading.Thread(target=spin_loop_task, args=(cid, message.from_user.username or str(cid))).start()
        else:
            if attempts < 3: bot.register_next_step_handler(bot.send_message(cid, f"❌ Invalid. {3-attempts} left. OTP:"), process_otp, attempts + 1)
            else: bot.send_message(cid, "❌ Max attempts."); remove_session(cid)
    except Exception as e: log_event(f"OTP Error: {e}", True); bot.send_message(cid, "[-] Critical error.")
def live_status_updater(cid, stop_event):
    while not stop_event.is_set():
        stop_event.wait(10)
        if stop_event.is_set(): break
        if cid in status_msg_ids:
            try: bot.edit_message_text(build_status_text(cid), chat_id=status_msg_ids[cid][0], message_id=status_msg_ids[cid][1], parse_mode="HTML")
            except: status_msg_ids.pop(cid, None)
def spin_loop_task(cid, username):
    global active_loops_count
    sd = active_sessions.get(cid)
    if not sd: return 
    p, mk, uk, dk, tk, tr = sd['phone'], sd['master_key'], sd['user_key'], sd['data_key'], sd['access_token'], sd['spin_count']
    active_loops_count += 1; active_users.add(cid)
    ub = DiscoverWorldBot(); ub.load_state(mk, uk, dk, tk)
    max_tr, stop_event = user_state['max_spins'], threading.Event()
    threading.Thread(target=live_status_updater, args=(cid, stop_event), daemon=True).start()
    lh = succ = canc = False; fr, ws = "None", 0
    try:
        while tr < max_tr:
            if bot_config['cloudflare_blocked']: time.sleep(2); continue
            if user_cancel_flags.get(cid): bot.send_message(cid, "🚫 Cancelled."); canc = True; user_cancel_flags[cid] = False; break
            tr += 1; api_s = cfb = False
            for _ in range(3):
                try:
                    ub.collect_keys(); raw = ub.post_signed_data("getReward", {"userKey": ub.user_key}); last_api_response[cid] = raw
                    if not raw: cfb = True; break
                    if 'rewardType' not in raw and 'isLimitReached' not in raw: time.sleep(random.uniform(0.5, 1.5)); continue
                    api_s = True; break
                except: time.sleep(random.uniform(1, 2))
            if cfb:
                if bot_config['cf_clearance']:
                    bot_config['cf_clearance'] = bot_config['user_agent'] = None; bot.send_message(cid, "⚠️ Cookie Expired. Clean Slate...")
                    ub = DiscoverWorldBot(); ub.load_state(mk, uk, dk, tk); tr -= 1; continue
                else:
                    bot_config['cloudflare_blocked'] = True; bot.send_message(cid, "🚨 <b>Blocked!</b> Use <code>/setcurl &lt;paste&gt;</code>", parse_mode="HTML")
                    while bot_config['cloudflare_blocked']:
                        if user_cancel_flags.get(cid): break
                        time.sleep(2)
                    if user_cancel_flags.get(cid): break
                    ub = DiscoverWorldBot(); ub.load_state(mk, uk, dk, tk); tr -= 1; continue
            if not api_s and not cfb: bot.send_message(cid, "[-] Crashed."); break
            rw, lr = raw.get('rewardType'), raw.get('isLimitReached'); update_spin_count(cid, tr)
            if rw and rw != "null": ws = 0
            else:
                ws += 1
                if ws >= 50: ws = 0; bot.send_message(cid, f"⚠️ <b>WARNING:</b> <code>{p}</code> 50 blanks.", parse_mode="HTML")
            if rw and rw not in ["BETTER_LUCK_NEXT_TIME", "null"]:
                bot.send_message(cid, f"🎉 <b>JACKPOT!</b> Won: {rw} on #{tr}!", parse_mode="HTML")
                log_event(f"🏆 WINNER: {username} {p} {rw}", False)
                if config_data.get("BROADCAST_CHANNEL"):
                    try: bot.send_message(config_data["BROADCAST_CHANNEL"], f"🎊 <b>@{username}</b> won <b>{rw}</b> in {tr} tries! 🎊", parse_mode="HTML")
                    except: pass
                succ = True; fr = rw; break
            if lr:
                mkup = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("🔄 Retry", callback_data=f"retry_{cid}"), telebot.types.InlineKeyboardButton("🔄 New", callback_data=f"continue_{cid}"))
                bot.send_message(cid, f"🛑 Limit reached after {tr}.\nRetry in 10m.", parse_mode="HTML", reply_markup=mkup); lh = True; break
            time.sleep(random.uniform(0.1, 0.3))
    finally:
        stop_event.set(); status_msg_ids.pop(cid, None)
        if succ: record_history(cid, p, "Won", fr, tr)
        elif lh: record_history(cid, p, "Limit Reached", "None", tr); retry_sessions[cid] = {'phone': p, 'master_key': mk, 'user_key': uk, 'data_key': dk, 'access_token': tk, 'timestamp': time.time()}
        elif canc: record_history(cid, p, "Cancelled", "None", tr)
        else:
            mkup = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("🔄 Retry", callback_data=f"retry_{cid}"), telebot.types.InlineKeyboardButton("🔄 New", callback_data=f"continue_{cid}"))
            bot.send_message(cid, f"⏹ <b>{tr} spins</b> done.\nRetry in 10m.", parse_mode="HTML", reply_markup=mkup)
            record_history(cid, p, "Failed", "None", tr); retry_sessions[cid] = {'phone': p, 'master_key': mk, 'user_key': uk, 'data_key': dk, 'access_token': tk, 'timestamp': time.time()}
        active_loops_count -= 1; active_users.discard(cid); remove_session(cid)
@bot.callback_query_handler(func=lambda c: c.data.startswith("retry_"))
def retry_callback(c):
    cid = c.message.chat.id
    if not is_authorized(cid): return bot.answer_callback_query(c.id, "⛔ Denied.")
    if bot_paused and cid != ADMIN_ID: return bot.answer_callback_query(c.id, "⏸️ Paused.")
    if cid in active_users: return bot.answer_callback_query(c.id, "⚠️ Loop running!")
    sd = retry_sessions.get(cid)
    if not sd: return bot.answer_callback_query(c.id, "❌ Expired. /start", show_alert=True)
    if time.time() - sd['timestamp'] > 600: retry_sessions.pop(cid, None); bot.send_message(cid, "⏳ >10m. /start"); return bot.answer_callback_query(c.id, "Expired.")
    bot.answer_callback_query(c.id, "🔄 Retrying...")
    save_session(cid, sd['phone'], sd['master_key'], sd['user_key'], sd['data_key'], sd['access_token'], 0)
    retry_sessions.pop(cid, None); user_cancel_flags[cid] = False
    bot.send_message(cid, f"🔄 Resuming {sd['phone']}..."); threading.Thread(target=spin_loop_task, args=(cid, c.from_user.username or str(cid))).start()
@bot.callback_query_handler(func=lambda c: c.data.startswith("continue_"))
def continue_callback(c):
    cid = c.message.chat.id; bot.clear_step_handler_by_chat_id(cid)
    if not is_authorized(cid): return bot.answer_callback_query(c.id, "⛔ Denied.")
    if bot_paused and cid != ADMIN_ID: return bot.answer_callback_query(c.id, "⏸️ Paused.")
    if cid in active_users: return bot.answer_callback_query(c.id, "⚠️ Loop running!")
    bot.answer_callback_query(c.id, "Starting new..."); user_cancel_flags[cid] = False; remove_session(cid)
    bot.register_next_step_handler(bot.send_message(cid, f"🏴‍☠️ Send 10-digit number:\n<i>(Max: {user_state['max_spins']})</i>", parse_mode="HTML"), process_phone)
if __name__ == "__main__":
    log_event("🏴‍☠️ Fleet Commander Initialized.", False)
    while True:
        try: bot.polling(none_stop=True, timeout=90, long_polling_timeout=10)
        except Exception as e:
            if "getaddrinfo failed" in str(e) or "11001" in str(e): log_event("Network fail. Retrying 20s...", False); time.sleep(20)
            else: log_event(f"Polling crashed: {e}", True); time.sleep(3)