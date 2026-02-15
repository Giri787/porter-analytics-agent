@echo off
setlocal EnableDelayedExpansion

echo ========================================================
echo   Porter Analytics Agent - GitHub Deployment Helper
echo ========================================================
echo.

:: Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Check if gh cli is installed
where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] GitHub CLI (gh) is not installed.
    echo This script requires GitHub CLI to automate the setup.
    echo.
    echo Please install it:
    echo 1. Download from https://cli.github.com/
    echo 2. Run the installer
    echo 3. Open a NEW terminal and run this script again
    pause
    exit /b 1
)

:: Login to GitHub if not already logged in
echo Checking GitHub authentication...
gh auth status >nul 2>nul
if %errorlevel% neq 0 (
    echo Please login to GitHub...
    gh auth login -w -p https
)

echo.
echo [1/3] Creating private repository...
set /p REPO_NAME="Enter a name for your repository (e.g., porter-analytics): "

:: Initialize git if not already
if not exist .git (
    git init
    git branch -M main
)

:: Create repo
gh repo create %REPO_NAME% --private --source=. --remote=origin --push

echo.
echo [2/3] Configuring Secrets...
echo Please ensure you have your .config/.env file ready with credentials.

if not exist config\.env (
    echo [ERROR] config\.env file not found!
    echo Please create it from config\.env.example first.
    pause
    exit /b 1
)

:: Read .env file and set secrets
for /f "usebackq tokens=1* delims==" %%a in ("config\.env") do (
    set "key=%%a"
    set "val=%%b"
    
    :: Skip comments and empty lines
    echo !key! | findstr /b /c:"#" >nul
    if !errorlevel! neq 0 (
        if not "!key!"=="" (
            echo Setting secret: !key!
            echo !val! | gh secret set !key! --repo %REPO_NAME%
        )
    )
)

echo Setting OAuth2 secrets...
if exist credentials.json (
    echo Setting secret: GOP_CREDENTIALS_JSON
    gh secret set GOP_CREDENTIALS_JSON < credentials.json --repo %REPO_NAME%
) else (
    echo [WARNING] credentials.json not found! Automation might fail.
)

if exist token.json (
    echo Setting secret: GOP_TOKEN_JSON
    gh secret set GOP_TOKEN_JSON < token.json --repo %REPO_NAME%
) else (
    echo [WARNING] token.json not found! Automation might fail.
    echo Please run 'python main.py' locally first to generate it.
)

echo.
echo [3/3] Verifying Deployment...
echo Triggering initial workflow run...
gh workflow run daily_analysis.yml --repo %REPO_NAME%

echo.
echo ========================================================
echo   Deployment Complete! 🚀
echo ========================================================
echo.
echo Your agent is now running on GitHub Actions.
echo You can view the status here:
echo https://github.com/%USERNAME%/%REPO_NAME%/actions
echo.
pause
