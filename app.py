"""HealthGuard: a health companion app written entirely in Python (Streamlit)."""
import copy
import math
import random
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

import ai
import core
import store

st.set_page_config(page_title="HealthGuard", page_icon="🛡️", layout="centered")

CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
.hg-hero {border-radius: 24px; padding: 20px; color: #fff; display: flex; align-items: center; gap: 14px; margin-bottom: 14px;}
.hg-hero h3 {margin: 0 0 4px 0; color: #fff; font-size: 1.25rem;}
.hg-hero p {margin: 0 0 6px 0; color: #fff; opacity: .93; font-size: .95rem;}
.hg-pill {display: inline-block; background: rgba(255,255,255,.2); border-radius: 999px; padding: 3px 10px; font-size: .75rem; color: #fff;}
.hg-sos {background: linear-gradient(180deg,#E53935,#B71C1C); border-radius: 24px; padding: 22px; text-align: center; color: #fff; margin-bottom: 12px;}
.hg-sos h2 {color: #fff; margin: 0; font-size: 2.2rem;}
.hg-sos p {color: #fff; margin: 6px 0 0 0;}
.hg-welcome {text-align: center; padding: 30px 0 10px 0;}
.hg-welcome h1 {color: #00695C; margin-bottom: 0;}
.hg-welcome p {color: #455A64;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- data helpers
def get_data():
    if "data" not in st.session_state:
        st.session_state["data"] = store.load()
    return st.session_state["data"]


def persist():
    store.save(st.session_state["data"])


def today_key():
    return date.today().isoformat()


def change_water(delta):
    d = get_data()
    d["water"][today_key()] = max(0, min(20, d["water"].get(today_key(), 0) + delta))
    persist()


def toggle_taken(med_id):
    d = get_data()
    ids = set(d["taken"].get(today_key(), []))
    ids.symmetric_difference_update({med_id})
    d["taken"] = {today_key(): sorted(ids)}  # only today matters, so old days are dropped
    persist()


def add_reading(hr, spo2, steps, sleep_hours):
    d = get_data()
    d["vitals"].append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "hr": hr, "spo2": spo2, "steps": steps,
        "sleep_min": int(round(sleep_hours * 60)) if sleep_hours else None,
    })
    d["vitals"] = d["vitals"][-3000:]
    persist()


def clean_text(text, limit):
    return text.replace("|", " ").replace("\n", " ").strip()[:limit]


# ---------------------------------------------------------------- shared pieces
def hero(title, subtitle, score, level, pill=""):
    colors = {
        core.NORMAL: ("#00695C", "#26A69A"),
        core.CAUTION: ("#E65100", "#FB8C00"),
        core.CRITICAL: ("#B71C1C", "#EF5350"),
    }[level]
    circ = 2 * math.pi * 42
    dash = circ * (score or 0) / 100
    label = "--" if score is None else str(score)
    ring = (
        '<svg width="96" height="96" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,.25)" stroke-width="10"/>'
        f'<circle cx="50" cy="50" r="42" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 50 50)"/>'
        f'<text x="50" y="55" text-anchor="middle" font-size="26" font-weight="600" fill="#fff">{label}</text>'
        '<text x="50" y="69" text-anchor="middle" font-size="10" fill="#fff" opacity=".85">score</text></svg>'
    )
    pill_html = f'<span class="hg-pill">{pill}</span>' if pill else ""
    st.markdown(
        f'<div class="hg-hero" style="background:linear-gradient(135deg,{colors[0]},{colors[1]})">'
        f'<div style="flex:1"><h3>{title}</h3><p>{subtitle}</p>{pill_html}</div>{ring}</div>',
        unsafe_allow_html=True,
    )


def alert_links(data, reason, hr, spo2):
    """Ready-to-tap SMS / WhatsApp / call links for every guardian, plus optional auto-SMS."""
    p = data["profile"]
    body = core.emergency_message(p["name"], reason, hr, spo2, p["location"])
    st.write("Send this message to your guardians:")
    st.code(body, language=None)
    if not data["contacts"]:
        st.warning("You have no emergency contacts yet. Add them in the SOS tab.")
    for i, c in enumerate(data["contacts"]):
        cols = st.columns([2, 1, 1, 1])
        cols[0].write(f"**{c['name']}**")
        cols[1].link_button("SMS", core.sms_link(c["phone"], body))
        cols[2].link_button("WhatsApp", core.whatsapp_link(c["phone"], body))
        cols[3].link_button("Call", core.call_link(c["phone"]))
    if data["contacts"] and core.twilio_configured():
        if st.button("Send SMS to all guardians automatically", key=f"twilio_{reason}"):
            for c in data["contacts"]:
                ok, msg = core.send_twilio_sms(c["phone"], body)
                (st.success if ok else st.error)(f"{c['name']}: {msg}")
    st.link_button("Call emergency services (112)", "tel:112")


# ---------------------------------------------------------------- screens
def welcome():
    st.markdown(
        '<div class="hg-welcome">'
        '<svg width="120" height="120" viewBox="0 0 108 108">'
        '<path d="M54 14 L90 28 V54 C90 76 74 90 54 98 C34 90 18 76 18 54 V28 Z" fill="#00897B"/>'
        '<polyline points="30,56 44,56 50,42 58,70 64,50 68,56 78,56" fill="none" stroke="#fff" '
        'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        "<h1>HealthGuard</h1><h4 style='color:#00897B;margin-top:0'>Your Health. Our Priority.</h4>"
        "<p>Track your health, stay safe, and get the support you need, all in one place.</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("Get Started", type="primary"):
        get_data()["profile"]["onboarded"] = True
        persist()
        st.rerun()
    st.caption("Not a medical device. In an emergency call 112.")


def home(data):
    p, vitals = data["profile"], data["vitals"]
    now = datetime.now()
    day = timedelta(hours=24)

    level, message, key = core.current_alert(vitals, now)
    hr = core.latest_value(vitals, "hr", day, now)
    spo2 = core.latest_value(vitals, "spo2", day, now)
    steps = core.steps_today(vitals)
    sleep = core.latest_value(vitals, "sleep_min", timedelta(hours=36), now)
    has_data = any(v is not None for v in (hr, spo2, steps, sleep))
    score = core.health_score(hr, spo2, steps, sleep, p["step_goal"]) if has_data else None

    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"
    title = f"{greeting}, {p['name']}" if p["name"].strip() else greeting
    if not has_data:
        subtitle = "Add your first readings below"
    elif level == core.NORMAL:
        subtitle = "Stay healthy, stay strong"
    else:
        subtitle = message
    pill = f"Wellness: {core.score_label(score)}" if score is not None else ""
    hero(title, subtitle, score, level, pill)

    if p.get("sample"):
        st.info("You're looking at sample data. Remove it in the Profile tab to start with your own readings.")

    # "Are you okay?" check-in for critical readings
    if level == core.CRITICAL and st.session_state.get("alert_ok_for") != key:
        st.error(f"🚨 {message}")
        st.write("**Are you okay?**")
        c1, c2 = st.columns(2)
        if c1.button("I'm okay", key="alert_ok"):
            st.session_state["alert_ok_for"] = key
            st.session_state.pop("need_help_for", None)
            st.rerun()
        if c2.button("I need help", key="alert_help", type="primary"):
            st.session_state["need_help_for"] = key
        if st.session_state.get("need_help_for") == key:
            alert_links(data, message, hr, spo2)

    with st.expander("➕ Log your readings"):
        st.caption("Type in what your watch, cuff or pulse oximeter shows. Leave a field at 0 to skip it.")
        with st.form("vitals_form", clear_on_submit=True):
            a, b = st.columns(2)
            hr_in = a.number_input("Heart rate (bpm)", min_value=0, max_value=250, value=0)
            spo2_in = b.number_input("Blood oxygen SpO2 (%)", min_value=0, max_value=100, value=0)
            steps_in = a.number_input("Steps today", min_value=0, max_value=100000, value=0, step=100)
            sleep_in = b.number_input("Sleep last night (hours)", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
            submitted = st.form_submit_button("Save readings", type="primary")
        if submitted:
            if hr_in and not 20 <= hr_in <= 250:
                st.error("Heart rate should be between 20 and 250.")
            elif spo2_in and not 50 <= spo2_in <= 100:
                st.error("SpO2 should be between 50 and 100.")
            elif not any((hr_in, spo2_in, steps_in, sleep_in)):
                st.warning("Enter at least one reading.")
            else:
                add_reading(hr_in or None, spo2_in or None, steps_in or None, sleep_in or None)
                st.rerun()

    # Vitals
    def hr_note(v):
        if v is None:
            return "No data"
        return "Low" if v < 50 else "Elevated" if v > 100 else "Normal"

    def o2_note(v):
        if v is None:
            return "No data"
        return "Healthy" if v >= 95 else "Low" if v >= 90 else "Very low"

    a, b = st.columns(2)
    with a.container(border=True):
        st.metric("❤️ Heart rate", f"{hr} bpm" if hr is not None else "--")
        st.caption(hr_note(hr))
    with b.container(border=True):
        st.metric("🩸 Blood oxygen", f"{spo2}%" if spo2 is not None else "--")
        st.caption(o2_note(spo2))
    a, b = st.columns(2)
    with a.container(border=True):
        st.metric("👟 Steps", f"{steps:,}" if steps is not None else "--")
        st.caption(f"Goal {p['step_goal']:,}")
    with b.container(border=True):
        st.metric("🌙 Sleep", core.mins_text(sleep) if sleep is not None else "--")
        st.caption("Last night")

    # Next medicine
    meds = sorted(data["medicines"], key=lambda m: m["time"])
    taken = set(data["taken"].get(today_key(), []))
    pending = [m for m in meds if m["id"] not in taken]
    nxt = next((m for m in pending if m["time"] >= now.strftime("%H:%M")), pending[0] if pending else None)
    if nxt:
        with st.container(border=True):
            dose = f", {nxt['dose']}" if nxt["dose"] else ""
            st.write(f"💊 **Next medicine:** {nxt['name']}{dose} at {core.clock_text(nxt['time'])}")

    series = core.hr_series(vitals, 24, now)
    if len(series) >= 2:
        with st.container(border=True):
            st.write("**Heart rate, last 24 hours**")
            st.line_chart(series, height=160)

    # Daily goals
    with st.container(border=True):
        st.write("**Today's goals**")
        goal = max(p["step_goal"], 1)
        st.progress(min((steps or 0) / goal, 1.0), text=f"👟 Steps  {steps or 0:,} / {goal:,}")
        sleep_h = (sleep or 0) / 60
        st.progress(min(sleep_h / 8, 1.0), text=f"🌙 Sleep  {core.mins_text(sleep or 0)} / 8h")
        water = data["water"].get(today_key(), 0)
        wgoal = max(p["water_goal"], 1)
        st.progress(min(water / wgoal, 1.0), text=f"💧 Water  {water} / {wgoal} glasses")
        a, b = st.columns(2)
        a.button("− 1 glass", on_click=change_water, args=(-1,), disabled=water <= 0)
        b.button("+ 1 glass", on_click=change_water, args=(1,))

    st.info("💡 " + core.pick_tip(hr, sleep, data["water"].get(today_key(), 0), steps, p["step_goal"], now.hour))
    st.caption("HealthGuard is not a medical device. In an emergency call 112.")


def history(data):
    st.subheader("Health Metrics")
    vitals, p = data["vitals"], data["profile"]
    choice = st.radio("Metric", ["Heart Rate", "Steps", "Sleep", "BP"], horizontal=True, label_visibility="collapsed")

    if choice == "Heart Rate":
        series = core.hr_series(vitals, 24)
        with st.container(border=True):
            st.metric("❤️ Latest heart rate", f"{core.latest_value(vitals, 'hr')} bpm" if series else "--")
            if len(series) >= 2:
                st.line_chart(series, height=200)
            else:
                st.caption("Log at least two heart rate readings to see a chart.")
        with st.container(border=True):
            st.write("**Last 24 hours**")
            a, b, c = st.columns(3)
            a.metric("Lowest", f"{min(series)} bpm" if series else "--")
            b.metric("Highest", f"{max(series)} bpm" if series else "--")
            c.metric("Average", f"{round(sum(series) / len(series))} bpm" if series else "--")

    elif choice == "Steps":
        week = core.daily_series(vitals, "steps", 7)
        values = [v for _, v in week]
        with st.container(border=True):
            st.metric("👟 Steps today", f"{core.steps_today(vitals) or 0:,}", f"goal {p['step_goal']:,}", delta_color="off")
            if any(values):
                st.bar_chart(pd.DataFrame({"Steps": values}, index=pd.to_datetime([d for d, _ in week])), height=220)
            else:
                st.caption("No step history yet.")
        with st.container(border=True):
            st.write("**This week**")
            nonzero = [v for v in values if v]
            a, b, c = st.columns(3)
            a.metric("Lowest", f"{min(nonzero):,}" if nonzero else "--")
            b.metric("Best", f"{max(nonzero):,}" if nonzero else "--")
            c.metric("Average", f"{round(sum(nonzero) / len(nonzero)):,}" if nonzero else "--")

    elif choice == "Sleep":
        week = core.daily_series(vitals, "sleep_min", 7)
        hours = [round(v / 60, 1) for _, v in week]
        last = core.latest_value(vitals, "sleep_min")
        with st.container(border=True):
            st.metric("🌙 Last night", core.mins_text(last) if last is not None else "--")
            if any(hours):
                st.bar_chart(pd.DataFrame({"Hours": hours}, index=pd.to_datetime([d for d, _ in week])), height=220)
            st.caption("Most adults do well with 7 to 9 hours.")

    else:
        bp = [l for l in reversed(data["logs"]) if l["type"] == "BP"]
        with st.container(border=True):
            st.write("**🩺 Blood pressure**")
            if not bp:
                st.caption("No readings yet. Add them in the Profile tab under Health Log, from a blood pressure cuff.")
            else:
                st.metric("Latest", f"{bp[0]['value']} mmHg")
                recent = list(reversed(bp[:10]))
                st.line_chart([float(l["value"].split("/")[0]) for l in recent], height=200)
                st.caption("The line shows the top number (systolic).")

    report = core.build_report(p, vitals, data["logs"], sample=p.get("sample", False))
    st.download_button("Download full report (.txt)", report, file_name="healthguard_report.txt")


def medicine(data):
    st.subheader("Medicine Reminders")
    st.success("💊 Stay on track with your medications. Never miss a dose!")
    now = datetime.now().strftime("%H:%M")
    taken = set(data["taken"].get(today_key(), []))
    meds = sorted(data["medicines"], key=lambda m: m["time"])
    if not meds:
        st.caption("No reminders yet. Add one below.")
    for m in meds:
        done = m["id"] in taken
        with st.container(border=True):
            a, b, c = st.columns([5, 2, 1])
            dose = f"  \n{m['dose']}" if m["dose"] else ""
            a.markdown(f"**{m['name']}**{dose}  \n{core.clock_text(m['time'])}")
            if not done and m["time"] <= now:
                a.caption("⏰ Due now")
            b.checkbox("Taken", value=done, key=f"taken_{m['id']}_{today_key()}", on_change=toggle_taken, args=(m["id"],))
            if c.button("🗑", key=f"del_med_{m['id']}", help="Delete reminder"):
                data["medicines"] = [x for x in data["medicines"] if x["id"] != m["id"]]
                persist()
                st.rerun()

    with st.expander("➕ Add reminder", expanded=not meds):
        with st.form("med_form", clear_on_submit=True):
            name = st.text_input("Medicine name")
            dose = st.text_input("Dose, e.g. 1 tablet after food")
            when = st.time_input("Time", value=time(8, 0))
            if st.form_submit_button("Save reminder", type="primary"):
                if not name.strip():
                    st.error("Enter the medicine name.")
                else:
                    data["medicines"].append({
                        "id": random.randint(1, 2**31 - 1),
                        "name": clean_text(name, 40), "dose": clean_text(dose, 40), "time": when.strftime("%H:%M"),
                    })
                    persist()
                    st.rerun()
    st.caption(
        "This web app shows what's due when you open it. It can't buzz your phone while closed. "
        "Set a phone alarm too for important doses."
    )


def sos(data):
    p = data["profile"]
    st.markdown('<div class="hg-sos"><h2>🆘 Emergency SOS</h2>'
                "<p>Your guardians will get your message and location.</p></div>", unsafe_allow_html=True)

    loc = st.text_input("Your current location (optional)", value=p["location"],
                        placeholder="Paste a Google Maps link or type your address")
    if loc != p["location"]:
        p["location"] = loc.strip()[:300]
        persist()

    sure = st.checkbox("I really need to send an SOS", key="sos_sure")
    if st.button("SEND SOS", type="primary", disabled=not sure):
        st.session_state["sos_open"] = True
    if st.session_state.get("sos_open"):
        alert_links(data, "SOS sent from the app", core.latest_value(data["vitals"], "hr", timedelta(hours=1)),
                    core.latest_value(data["vitals"], "spo2", timedelta(hours=1)))
        if st.button("Close"):
            st.session_state["sos_open"] = False
            st.session_state["sos_sure"] = False
            st.rerun()
    else:
        st.link_button("📞 Call emergency services (112)", "tel:112")

    st.subheader("Emergency contacts")
    if not data["contacts"]:
        st.caption("Add someone who should be alerted in an emergency.")
    for i, c in enumerate(data["contacts"]):
        with st.container(border=True):
            a, b, d = st.columns([4, 1, 1])
            a.markdown(f"**{c['name']}**  \n{c['phone']}")
            b.link_button("📞", core.call_link(c["phone"]))
            if d.button("🗑", key=f"del_c_{i}", help="Remove contact"):
                data["contacts"].pop(i)
                persist()
                st.rerun()
    with st.form("contact_form", clear_on_submit=True):
        name = st.text_input("Name")
        phone = st.text_input("Phone number")
        if st.form_submit_button("Add contact"):
            if not name.strip() or not core.valid_phone(phone):
                st.error("Enter a name and a valid phone number (at least 10 digits).")
            elif len(data["contacts"]) >= 5:
                st.error("You can save up to 5 contacts.")
            else:
                data["contacts"].append({"name": clean_text(name, 40), "phone": clean_text(phone, 20)})
                persist()
                st.rerun()
    if core.twilio_configured():
        st.caption("Automatic SMS is on (Twilio).")
    else:
        st.caption("To send SMS automatically, add Twilio settings (see README). Until then, the buttons open your "
                   "SMS or WhatsApp app with the message filled in.")


def assistant(data):
    st.subheader("Ask HealthGuard AI")
    st.caption("General information only, not medical advice. In an emergency call 112.")
    chat = st.session_state.setdefault("chat", [
        ("assistant", "Hi, I can help with small health doubts and precautions. I'm not a doctor, "
                      "so for anything serious call 112 or see a doctor."),
    ])
    vitals = data["vitals"]
    context = ai.describe(
        core.latest_value(vitals, "hr", timedelta(hours=24)), core.latest_value(vitals, "spo2", timedelta(hours=24)),
        core.steps_today(vitals), core.latest_value(vitals, "sleep_min", timedelta(hours=36)),
    )

    def send(question):
        question = question.strip()
        if not question:
            return
        history = list(chat)
        chat.append(("user", question))
        if core.has_red_flag(question):
            chat.append(("assistant", "This could be serious. Please call 112 or get to a hospital now. "
                                      "Don't wait for an app to answer."))
        with st.spinner("Thinking..."):
            chat.append(("assistant", ai.ask(question, context, history)))

    for role, text in chat:
        with st.chat_message(role):
            st.write(text)

    if len(chat) <= 1:
        cols = st.columns(2)
        for i, q in enumerate(["I feel a little dizzy", "Explain my heart rate", "Tips to sleep better", "Headache precautions"]):
            if cols[i % 2].button(q, key=f"sugg_{i}"):
                send(q)
                st.rerun()

    question = st.chat_input("Describe how you feel")
    if question:
        send(question)
        st.rerun()

    st.divider()
    st.subheader("Health tips")
    for emoji, title, text in core.GENERAL_TIPS:
        st.markdown(f"{emoji} **{title}**  \n{text}")


def profile(data):
    p = data["profile"]
    st.subheader("Profile")

    with st.form("profile_form"):
        name = st.text_input("Your name", value=p["name"])
        a, b = st.columns(2)
        age = a.text_input("Age", value=p["age"])
        blood = b.text_input("Blood group (optional)", value=p["blood_group"])
        c, d = st.columns(2)
        step_goal = c.number_input("Daily step goal", 2000, 30000, int(p["step_goal"]), step=500)
        water_goal = d.number_input("Daily water goal (glasses)", 1, 20, int(p["water_goal"]))
        if st.form_submit_button("Save", type="primary"):
            p["name"] = clean_text(name, 30)
            p["age"] = "".join(ch for ch in age if ch.isdigit())[:3]
            p["blood_group"] = clean_text(blood, 5).upper()
            p["step_goal"], p["water_goal"] = int(step_goal), int(water_goal)
            persist()
            st.toast("Saved ✅")
            st.rerun()

    st.subheader("Health log")
    st.caption("Blood pressure, weight and sugar readings you type in.")
    with st.form("log_form", clear_on_submit=True):
        kind = st.radio("Type", ["BP", "Weight", "Sugar"], horizontal=True)
        value = st.text_input("Value", placeholder="BP like 120/80, weight in kg, sugar in mg/dL")
        if st.form_submit_button("Save reading"):
            v = clean_text(value, 20)
            ok = (
                len(v.split("/")) == 2 and all(x.isdigit() and 2 <= len(x) <= 3 for x in v.split("/"))
                if kind == "BP" else _is_number(v)
            )
            if ok:
                data["logs"].insert(0, {"ts": datetime.now().isoformat(timespec="seconds"), "type": kind, "value": v})
                data["logs"] = data["logs"][:200]
                persist()
                st.rerun()
            else:
                st.error("Enter a valid value, for example 120/80 for blood pressure.")
    units = {"BP": "mmHg", "Weight": "kg", "Sugar": "mg/dL"}
    for i, entry in enumerate(data["logs"][:10]):
        a, b = st.columns([6, 1])
        when = datetime.fromisoformat(entry["ts"]).strftime("%d %b, %I:%M %p")
        a.write(f"**{entry['type']}** {entry['value']} {units[entry['type']]}  ·  {when}")
        if b.button("🗑", key=f"del_log_{i}", help="Delete entry"):
            data["logs"].pop(i)
            persist()
            st.rerun()

    st.subheader("Data")
    if p.get("sample"):
        if st.button("Remove sample data"):
            data["vitals"] = []
            p["sample"] = False
            persist()
            st.rerun()
    else:
        if st.button("Load sample data (to try the app)"):
            data["vitals"] = core.sample_vitals()
            p["sample"] = True
            persist()
            st.rerun()
    with st.expander("Erase everything"):
        st.warning("This deletes your profile, contacts, readings, reminders and logs from this app.")
        if st.checkbox("Yes, erase everything") and st.button("Erase now"):
            st.session_state["data"] = copy.deepcopy(store.DEFAULT)
            st.session_state["data"]["profile"]["onboarded"] = True
            persist()
            st.rerun()

    with st.expander("Help and support"):
        st.markdown(
            "**How do emergency alerts work?** When a critical reading is logged, HealthGuard asks "
            "\"Are you okay?\". If you tap *I need help*, you get ready-made SMS and WhatsApp messages for your "
            "guardians. The SOS tab does the same on demand.\n\n"
            "**Why no automatic watch data?** Your watch's app doesn't share data with this app, so readings are "
            "typed in. This version also only runs while it's open.\n\n"
            "**Is HealthGuard a medical device?** No. It gives general information and does not diagnose "
            "anything. In an emergency call 112."
        )


def _is_number(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- main
def main():
    data = get_data()
    if not data["profile"]["onboarded"]:
        welcome()
        return
    tabs = st.tabs(["🏠 Home", "📈 History", "💊 Medicine", "🆘 SOS", "🤖 Ask AI", "👤 Profile"])
    with tabs[0]:
        home(data)
    with tabs[1]:
        history(data)
    with tabs[2]:
        medicine(data)
    with tabs[3]:
        sos(data)
    with tabs[4]:
        assistant(data)
    with tabs[5]:
        profile(data)


main()
