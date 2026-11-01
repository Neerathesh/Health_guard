@echo off
REM Double-click to start HealthGuard on Windows.
REM Optional: set your keys here (remove the word REM at the start of a line).
REM set ANTHROPIC_API_KEY=paste-your-key-here
REM set TWILIO_SID=...
REM set TWILIO_TOKEN=...
REM set TWILIO_FROM=+1xxxxxxxxxx
python -m streamlit run app.py --server.address 0.0.0.0
pause
