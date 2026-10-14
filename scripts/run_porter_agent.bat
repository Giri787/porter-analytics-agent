@echo off
:: Porter Analytics Agent Launcher
:: Ensure we're in the correct directory
cd /d "C:\Users\anubh\.gemini\antigravity\scratch\porter-analytics-agent"

:: Run the agent
echo Starting Porter Analytics Agent...
python main.py >> "C:\Users\anubh\.gemini\antigravity\scratch\porter-analytics-agent\scheduler_output.log" 2>&1

:: Check exit code
if %ERRORLEVEL% equ 0 (
    echo Success!
) else (
    echo Failed with error code %ERRORLEVEL%
)
