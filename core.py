"""Health logic with no screens in it: warning rules, score, tips, alert messages."""
import math
import os
import urllib.parse
from datetime import date, datetime, timedelta

NORMAL, CAUTION, CRITICAL = "normal", "caution", "critical"
DEFAULT_COUNTRY_CODE = os.environ.get("HEALTHGUARD_COUNTRY_CODE", "91")


# ---------- Warning rules (simple on purpose, NOT medical thresholds) ----------
def evaluate(hr, spo2):
    """Returns (level, message). Rules are deterministic so alerts are predictable."""
    if spo2 is not None and spo2 < 90:
        return CRITICAL, f"Blood oxygen is very low ({spo2}%)"
    if hr is not None and hr > 150:
        return CRITICAL, f"Heart rate is very high ({hr} bpm)"
    if hr is not None and hr < 40:
        return CRITICAL, f"Heart rate is very low ({hr} bpm)"
    if spo2 is not None and spo2 < 94:
        return CAUTION, f"Blood oxygen is a little low ({spo2}%)"
    if hr is not None and hr > 120:
        return CAUTION, f"Heart rate is high ({hr} bpm). Rest and breathe slowly."
    if hr is not None and hr < 50:
        return CAUTION, f"Heart rate is low ({hr} bpm)"
    return NORMAL, ""


def parse_ts(text):
    return datetime.fromisoformat(text)


def latest_value(vitals, key, max_age=None, now=None):
    """Newest non-empty value of `key`. If max_age is given, ignore readings older than that."""
    now = now or datetime.now()
    for v in reversed(vitals):
        val = v.get(key)
        if val is None:
            continue
        if max_age is not None and now - parse_ts(v["ts"]) > max_age:
            return None
        return val
    return None


def current_alert(vitals, now=None):
    """Looks only at readings from the last 60 minutes. Returns (level, message, key)."""
    now = now or datetime.now()
    window = timedelta(minutes=60)
    hr = latest_value(vitals, "hr", window, now)
    spo2 = latest_value(vitals, "spo2", window, now)
    level, message = evaluate(hr, spo2)
    key = ""
    for v in reversed(vitals):
        if v.get("hr") is not None or v.get("spo2") is not None:
            key = v["ts"]
            break
    return level, message, key


def steps_today(vitals, today=None):
    today = (today or date.today()).isoformat()
    values = [v["steps"] for v in vitals if v.get("steps") is not None and v["ts"][:10] == today]
    return max(values) if values else None


def hr_series(vitals, hours=24, now=None):
    now = now or datetime.now()
    cutoff = now - timedelta(hours=hours)
    return [v["hr"] for v in vitals if v.get("hr") is not None and parse_ts(v["ts"]) >= cutoff]


def daily_series(vitals, key, days=7, today=None, mode="max"):
    """Per-day values for the last `days` days, oldest first: list of (date, value)."""
    today = today or date.today()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        values = [v[key] for v in vitals if v.get(key) is not None and v["ts"][:10] == d.isoformat()]
        if not values:
            out.append((d, 0))
        elif mode == "avg":
            out.append((d, round(sum(values) / len(values))))
        else:
            out.append((d, max(values)))
    return out


# ---------- Score and tips ----------
def health_score(hr, spo2, steps, sleep_min, step_goal):
    """0 to 100 wellness score. For motivation only, not a medical measurement."""
    level, _ = evaluate(hr, spo2)
    vitals = {NORMAL: 50.0, CAUTION: 30.0, CRITICAL: 10.0}[level]
    activity = min(1.0, (steps or 0) / max(step_goal, 1)) * 25.0
    sleep = min(1.0, ((sleep_min or 0) / 60.0) / 7.5) * 25.0
    return max(0, min(100, round(vitals + activity + sleep)))


def score_label(score):
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    return "Needs attention"


def pick_tip(hr, sleep_min, water, steps, step_goal, hour):
    if hr is not None and hr > 100:
        return "Your heart rate is a bit high. Sit down and breathe slowly for a minute."
    if sleep_min is not None and sleep_min / 60 < 6:
        return "You slept under 6 hours. Try winding down earlier tonight."
    if water < 4:
        return "Drink a glass of water now. Small sips through the day add up."
    if hour >= 16 and (steps or 0) < step_goal / 2:
        return "A 10 minute walk would bring you closer to your step goal."
    return "Nice work. Keep your routine going today."


GENERAL_TIPS = [
    ("💧", "Stay hydrated", "Drink at least 8 glasses of water daily."),
    ("🍎", "Eat balanced meals", "Include fruits, vegetables and whole grains."),
    ("🏃", "Stay active", "Aim for at least 30 minutes of exercise daily."),
    ("🌙", "Get good sleep", "7 to 9 hours of quality sleep supports your health."),
    ("🧘", "Take a breather", "A few slow breaths can help when you feel stressed."),
    ("🩺", "Check in with a doctor", "Regular checkups catch problems early."),
]

RED_FLAGS = (
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "unconscious", "stroke", "seizure", "severe bleeding", "fainted",
)


def has_red_flag(text):
    t = text.lower()
    return any(flag in t for flag in RED_FLAGS)


def mins_text(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m}m"


def clock_text(hhmm):
    return datetime.strptime(hhmm, "%H:%M").strftime("%I:%M %p").lstrip("0")


# ---------- Emergency messages and links ----------
def normalize_phone(phone):
    """Digits only, with a country code. 10-digit numbers get the default code (India: 91)."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        digits = DEFAULT_COUNTRY_CODE + digits
    return digits


def valid_phone(phone):
    return len("".join(c for c in phone if c.isdigit())) >= 10


def emergency_message(name, reason, hr=None, spo2=None, location=""):
    who = name.strip() or "Someone you know"
    parts = [f"HealthGuard ALERT: {who} may be having a health emergency. {reason}."]
    if hr is not None or spo2 is not None:
        parts.append(f"HR {hr if hr is not None else '-'} bpm, SpO2 {spo2 if spo2 is not None else '-'}%.")
    if location.strip():
        parts.append(f"Location: {location.strip()}")
    parts.append("Please call them now.")
    return " ".join(parts)


def sms_link(phone, body):
    return f"sms:+{normalize_phone(phone)}?body={urllib.parse.quote(body)}"


def whatsapp_link(phone, body):
    return f"https://wa.me/{normalize_phone(phone)}?text={urllib.parse.quote(body)}"


def call_link(phone):
    return f"tel:+{normalize_phone(phone)}"


def twilio_configured():
    return all(os.environ.get(k) for k in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM"))


def send_twilio_sms(phone, body):
    """Optional automatic SMS through Twilio. Returns (ok, message)."""
    if not twilio_configured():
        return False, "Twilio is not set up."
    import requests
    sid = os.environ["TWILIO_SID"]
    try:
        r = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, os.environ["TWILIO_TOKEN"]),
            data={"To": "+" + normalize_phone(phone), "From": os.environ["TWILIO_FROM"], "Body": body},
            timeout=20,
        )
        if r.status_code in (200, 201):
            return True, "Sent"
        return False, f"Twilio error {r.status_code}"
    except Exception as e:  # network problems must not crash the app
        return False, f"Couldn't reach Twilio ({type(e).__name__})"


# ---------- Report ----------
def build_report(profile, vitals, logs, sample=False):
    today = date.today().strftime("%d %b %Y")
    hrs = hr_series(vitals, 24)
    hr = latest_value(vitals, "hr")
    lines = [f"HealthGuard summary, {today}"]
    if sample:
        lines.append("NOTE: sample data, not real readings")
    if profile.get("name"):
        lines.append(f"Name: {profile['name']}")
    extra = f" (last 24h low {min(hrs)}, high {max(hrs)}, average {round(sum(hrs) / len(hrs))})" if hrs else ""
    lines.append(f"Heart rate: {hr if hr is not None else '-'} bpm{extra}")
    spo2 = latest_value(vitals, "spo2")
    lines.append(f"Blood oxygen: {spo2 if spo2 is not None else '-'}%")
    steps = steps_today(vitals)
    lines.append(f"Steps today: {steps if steps is not None else '-'}")
    sleep = latest_value(vitals, "sleep_min")
    lines.append(f"Sleep last night: {mins_text(sleep) if sleep is not None else '-'}")
    bp = next((l for l in reversed(logs) if l["type"] == "BP"), None)
    if bp:
        lines.append(f"Latest blood pressure: {bp['value']} mmHg")
    lines.append("Made with HealthGuard. This is not a medical document.")
    return "\n".join(lines)


# ---------- Sample data (clearly marked in the app) ----------
def sample_vitals(now=None):
    """A week of believable readings so every chart has something to show."""
    now = now or datetime.now()
    steps = [5200, 7800, 6100, 9300, 4500, 8200, 6482]
    hr_avg = [71, 73, 70, 74, 72, 75, 72]
    sleep = [410, 450, 395, 480, 430, 470, 440]
    out = []
    for i in range(6, -1, -1):
        idx = 6 - i
        if i == 0:  # today: times counted back from now, so nothing is in the future
            hr_times = [now - timedelta(hours=6), now - timedelta(hours=4), now - timedelta(hours=2),
                        now - timedelta(minutes=10)]
            summary_time = now - timedelta(minutes=1)
        else:
            day = (now - timedelta(days=i)).replace(hour=9, minute=0, second=0, microsecond=0)
            hr_times = [day + timedelta(hours=h * 3) for h in range(4)]
            summary_time = day + timedelta(hours=11)
        for h, t in enumerate(hr_times):
            out.append({
                "ts": t.isoformat(timespec="seconds"),
                "hr": hr_avg[idx] + (h % 3) * 2 - 2, "spo2": 97 - (h % 2), "steps": None, "sleep_min": None,
            })
        out.append({
            "ts": summary_time.isoformat(timespec="seconds"),
            "hr": None, "spo2": None, "steps": steps[idx], "sleep_min": sleep[idx],
        })
    out.sort(key=lambda v: v["ts"])
    return out
