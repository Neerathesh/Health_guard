# HealthGuard (Python)

The whole app in Python, using Streamlit. No Android Studio, no Kotlin, no Node server.

What it does
- Welcome screen, then six tabs: Home, History, Medicine, SOS, Ask AI, Profile
- Home: wellness score, heart rate, SpO2, steps, sleep, goals, water tracker, next medicine, daily tip
- Log your readings by typing them in (from a watch screen, pulse oximeter or BP cuff)
- Warning rules + "Are you okay?" check-in on critical readings
- Guardian alerts: ready-made SMS / WhatsApp / call buttons with your readings and location
- History: heart rate, steps, sleep and BP charts, plus a downloadable report
- Medicine reminders with "taken" ticks, health log (BP, weight, sugar), profile
- Ask AI (needs an API key) with safety rules and emergency red-flag detection

What it does NOT do (be honest in your demo)
- No automatic watch data. Your watch's app doesn't share data with other apps, so readings are typed in.
- It only runs while the app is open. A web app cannot watch you or buzz your phone in the background.
- SMS is not sent automatically unless you set up Twilio. Otherwise the buttons open your SMS or WhatsApp app with the message filled in.

## Set up (Windows, about 5 minutes)

1. Install Python 3.10 or newer from python.org. On the first screen tick "Add python.exe to PATH".
2. Open the HealthGuard folder, click its address bar, type `cmd`, press Enter.
3. Install the libraries (once):
       pip install -r requirements.txt
4. Start the app:
       python -m streamlit run app.py
   or double-click `run_healthguard.bat`.
5. Your browser opens the app. Press "Get Started".

## Open it on your phone
1. Phone and laptop on the same Wi-Fi.
2. Start with: `python -m streamlit run app.py --server.address 0.0.0.0` (the .bat file already does this).
3. In the window, find "Network URL", for example http://192.168.1.5:8501, and open it in your phone's browser.
4. Windows may ask about the firewall: choose "Allow".
5. In Chrome: menu, "Add to Home screen" to get an icon.

## Turn on the AI assistant
1. Get a key at console.anthropic.com (usage is billed, keep the key private).
2. Before starting the app, set it:
       PowerShell:  $env:ANTHROPIC_API_KEY="paste-your-key-here"
       cmd:         set ANTHROPIC_API_KEY=paste-your-key-here
   or remove the REM from that line in `run_healthguard.bat`.
3. Start the app. The key stays on your laptop and never goes to the browser.

## Optional: automatic SMS (Twilio)
Set TWILIO_SID, TWILIO_TOKEN and TWILIO_FROM the same way. A "Send SMS to all guardians automatically" button then appears.
Indian numbers without a country code are treated as +91. Change it with HEALTHGUARD_COUNTRY_CODE.

## Files
- app.py: all screens
- core.py: warning rules, score, tips, alert messages and links (no screens inside)
- store.py: saves everything to healthguard_data.json
- ai.py: the assistant
- tests/: 13 automatic tests. Run them with: `python -m pytest -q tests`

Your data is saved in `healthguard_data.json` next to app.py. Delete it to start fresh.

HealthGuard is not a medical device. In an emergency call 112.
